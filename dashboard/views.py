import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.models import User
from items.models import ItemReport, Category, ReportImage, ItemMatch, ReportReview, AdminContactLog, AuditLog
from items.forms import AdminReportReviewForm, AdminContactLogForm
from items.services.report_workflow import update_report_approval
from items.services.ai_matching import run_ai_matching_for_report
from claims.models import OwnershipClaim, RecoveryRecord
from claims.forms import AdminClaimReviewForm, RecoveryCompletionForm
from notifications.models import Notification


def admin_required(view_func):
    """Decorator ensuring only users with staff or admin role can access."""
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not getattr(request.user, 'is_admin_or_staff', False):
            raise PermissionDenied("You do not have administrative permissions to access the campus control dashboard.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@admin_required
def admin_overview_view(request):
    """
    Central administrative dashboard overview.
    Metrics calculated directly from live database records.
    """
    total_reports = ItemReport.objects.count()
    pending_reports = ItemReport.objects.filter(approval_status='PENDING').count()
    needs_info_reports = ItemReport.objects.filter(approval_status='NEEDS_INFORMATION').count()
    approved_reports = ItemReport.objects.filter(approval_status='APPROVED').count()
    rejected_reports = ItemReport.objects.filter(approval_status='REJECTED').count()
    active_matches = ItemMatch.objects.filter(is_active=True).count()
    pending_claims = OwnershipClaim.objects.filter(status='PENDING_REVIEW').count()
    recovered_items = RecoveryRecord.objects.count()

    # Recent submissions awaiting review
    recent_pending = ItemReport.objects.filter(
        approval_status__in=['PENDING', 'NEEDS_INFORMATION']
    ).select_related('category', 'reporter').prefetch_related('images').order_by('-created_at')[:6]

    # High probability matches requiring admin inspection
    top_matches = ItemMatch.objects.filter(
        is_active=True
    ).select_related(
        'lost_report', 'found_report', 'lost_report__category', 'found_report__category'
    ).order_by('-similarity_score')[:5]

    # Recent Administrative Audit Activity
    recent_actions = AuditLog.objects.select_related('actor').order_by('-created_at')[:8]

    # Chart data: Type distribution
    lost_count = ItemReport.objects.filter(report_type='LOST').count()
    found_count = ItemReport.objects.filter(report_type='FOUND').count()

    # Category distribution for Chart.js
    category_counts = list(
        Category.objects.annotate(
            report_count=Count('reports')
        ).values('name', 'report_count')
    )

    context = {
        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'needs_info_reports': needs_info_reports,
        'approved_reports': approved_reports,
        'rejected_reports': rejected_reports,
        'active_matches': active_matches,
        'pending_claims': pending_claims,
        'recovered_items': recovered_items,
        'recent_pending': recent_pending,
        'top_matches': top_matches,
        'recent_actions': recent_actions,
        'lost_count': lost_count,
        'found_count': found_count,
        'category_chart_json': json.dumps(category_counts),
        'status_chart_json': json.dumps({
            'Pending': pending_reports,
            'Approved': approved_reports,
            'Needs Info': needs_info_reports,
            'Rejected': rejected_reports,
            'Recovered': recovered_items,
        })
    }
    return render(request, 'dashboard/overview.html', context)


@admin_required
def admin_approvals_view(request):
    """
    Dedicated reports management and approval queue page.
    """
    queryset = ItemReport.objects.select_related('category', 'reporter').prefetch_related('images').all()

    # Filtering
    status_filter = request.GET.get('status', 'PENDING')
    if status_filter and status_filter != 'ALL':
        queryset = queryset.filter(approval_status=status_filter)

    type_filter = request.GET.get('type')
    if type_filter in ('LOST', 'FOUND'):
        queryset = queryset.filter(report_type=type_filter)

    category_id = request.GET.get('category')
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    search_query = request.GET.get('q', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(report_id__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(reporter__username__icontains=search_query) |
            Q(reporter__first_name__icontains=search_query) |
            Q(location_name__icontains=search_query)
        )

    queryset = queryset.order_by('-created_at')

    paginator = Paginator(queryset, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'status_filter': status_filter,
        'type_filter': type_filter or 'ALL',
        'category_filter': category_id or '',
        'search_query': search_query,
        'total_count': queryset.count(),
    }
    return render(request, 'dashboard/approvals.html', context)


@admin_required
def admin_report_inspect_view(request, report_id):
    """
    Detailed administrator inspection page for an individual report.
    Displays private reporter information, distinctive markings, photos, AI matches,
    review decision action form, and contact log creator.
    """
    report = get_object_or_404(ItemReport, report_id=report_id)

    # Forms
    review_form = AdminReportReviewForm(initial={
        'action': report.approval_status if report.approval_status in ['APPROVE', 'REJECT', 'NEEDS_INFORMATION', 'ARCHIVED'] else 'APPROVE',
        'reason': report.rejection_reason,
        'admin_notes': ''
    })
    contact_form = AdminContactLogForm(initial={
        'contact_target': report.reporter,
        'contact_method': report.contact_preference if report.contact_preference in ['EMAIL', 'PHONE'] else 'EMAIL',
        'contact_details_used': report.contact_email or report.contact_phone,
    })

    if request.method == 'POST':
        action_type = request.POST.get('form_type')

        if action_type == 'review_decision':
            review_form = AdminReportReviewForm(request.POST)
            if review_form.is_valid():
                action = review_form.cleaned_data['action']
                reason = review_form.cleaned_data['reason']
                notes = review_form.cleaned_data['admin_notes']

                target_status = action
                if action == 'APPROVE':
                    target_status = 'APPROVED'
                elif action == 'REJECT':
                    target_status = 'REJECTED'
                elif action == 'NEEDS_INFORMATION':
                    target_status = 'NEEDS_INFORMATION'
                elif action == 'ARCHIVED':
                    target_status = 'ARCHIVED'

                try:
                    update_report_approval(
                        report=report,
                        admin_user=request.user,
                        new_status=target_status,
                        reason=reason,
                        notes=notes,
                        request_ip=request.META.get('REMOTE_ADDR')
                    )
                    messages.success(
                        request,
                        f"Report [{report.report_id}] status transitioned to {target_status}."
                    )
                    return redirect('dashboard:report_inspect', report_id=report.report_id)
                except ValueError as err:
                    messages.error(request, str(err))

        elif action_type == 'log_contact':
            contact_form = AdminContactLogForm(request.POST)
            if contact_form.is_valid():
                log_entry = contact_form.save(commit=False)
                log_entry.report = report
                log_entry.admin = request.user
                log_entry.save()

                AuditLog.objects.create(
                    actor=request.user,
                    action_type='CONTACT_LOGGED',
                    target_model='AdminContactLog',
                    target_id=str(log_entry.id),
                    details=f"Admin contacted {log_entry.contact_target.username} via {log_entry.contact_method} (Outcome: {log_entry.outcome})",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                messages.success(request, "Student contact attempt recorded in verification log.")
                return redirect('dashboard:report_inspect', report_id=report.report_id)

        elif action_type == 'trigger_ai':
            run_ai_matching_for_report(report)
            messages.success(request, "AI matching engine executed. Potential match scores updated.")
            return redirect('dashboard:report_inspect', report_id=report.report_id)

    # Fetch AI matches involving this report
    if report.report_type == 'LOST':
        matches = report.matches_as_lost.filter(is_active=True).select_related('found_report', 'found_report__reporter')
    else:
        matches = report.matches_as_found.filter(is_active=True).select_related('lost_report', 'lost_report__reporter')

    contact_logs = report.contact_logs.select_related('admin', 'contact_target').order_by('-created_at')
    review_history = report.reviews.select_related('reviewer').order_by('-created_at')

    context = {
        'report': report,
        'review_form': review_form,
        'contact_form': contact_form,
        'matches': matches,
        'contact_logs': contact_logs,
        'review_history': review_history,
    }
    return render(request, 'dashboard/report_inspect.html', context)


@admin_required
def admin_matches_view(request):
    """
    AI Match Review console: Side-by-side inspection of potential recovery pairs.
    """
    queryset = ItemMatch.objects.filter(is_active=True).select_related(
        'lost_report', 'found_report', 'lost_report__reporter', 'found_report__reporter',
        'lost_report__category', 'found_report__category'
    ).prefetch_related(
        'lost_report__images', 'found_report__images'
    )

    status_filter = request.GET.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    min_score = request.GET.get('min_score')
    if min_score:
        try:
            queryset = queryset.filter(similarity_score__gte=float(min_score))
        except ValueError:
            pass

    queryset = queryset.order_by('-similarity_score')

    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter or 'ALL',
        'min_score': min_score or '',
        'total_count': queryset.count(),
    }
    return render(request, 'dashboard/matches_list.html', context)


@admin_required
def admin_update_match_status(request, match_id):
    """Update review status of an AI match (e.g. mark as Under Review or Dismiss)."""
    match = get_object_or_404(ItemMatch, id=match_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('admin_notes', '')

        if new_status in dict(ItemMatch.MATCH_STATUS_CHOICES):
            match.status = new_status
            if notes:
                match.admin_notes = f"{match.admin_notes}\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {request.user.username}: {notes}".strip()
            match.save()

            AuditLog.objects.create(
                actor=request.user,
                action_type='MATCH_STATUS_UPDATED',
                target_model='ItemMatch',
                target_id=str(match.id),
                details=f"Admin {request.user.username} set match {match.lost_report.report_id} <-> {match.found_report.report_id} to {new_status}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f"Match status updated to {match.get_status_display()}.")

    return redirect('dashboard:matches_list')


@admin_required
def admin_claims_view(request):
    """Manage ownership claims queue."""
    claims = OwnershipClaim.objects.select_related(
        'item_report', 'claimant', 'reviewer'
    ).order_by('-created_at')

    status_filter = request.GET.get('status')
    if status_filter:
        claims = claims.filter(status=status_filter)

    paginator = Paginator(claims, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/claims_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter or 'ALL',
    })


@admin_required
def admin_claim_inspect_view(request, claim_id):
    """
    Detailed claim review page.
    Compares student's submitted evidence directly with item's confidential distinctive marks.
    """
    claim = get_object_or_404(OwnershipClaim, claim_id=claim_id)

    review_form = AdminClaimReviewForm(instance=claim)
    recovery_form = RecoveryCompletionForm()

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'review_claim':
            review_form = AdminClaimReviewForm(request.POST, instance=claim)
            if review_form.is_valid():
                updated_claim = review_form.save(commit=False)
                updated_claim.reviewer = request.user
                updated_claim.resolved_at = timezone.now()
                updated_claim.save()

                # Notify claimant
                Notification.objects.create(
                    recipient=claim.claimant,
                    title=f"Claim Status Update: [{claim.claim_id}]",
                    message=f"Your claim for {claim.item_report.title} status is now: {claim.get_status_display()}.",
                    link=f"/claims/detail/{claim.claim_id}/",
                    notification_type='CLAIM_UPDATE'
                )

                AuditLog.objects.create(
                    actor=request.user,
                    action_type='CLAIM_REVIEWED',
                    target_model='OwnershipClaim',
                    target_id=claim.claim_id,
                    details=f"Admin {request.user.username} updated claim status to {claim.status}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                messages.success(request, f"Claim status updated to {claim.get_status_display()}.")
                return redirect('dashboard:claim_inspect', claim_id=claim.claim_id)

        elif form_type == 'finalize_recovery':
            recovery_form = RecoveryCompletionForm(request.POST)
            if recovery_form.is_valid():
                with transaction.atomic():
                    recovery = RecoveryRecord.objects.create(
                        found_report=claim.item_report,
                        claim=claim,
                        recovered_by=claim.claimant,
                        returned_by_name=recovery_form.cleaned_data['returned_by_name'],
                        admin=request.user,
                        verification_summary=recovery_form.cleaned_data['verification_summary'],
                        notes=recovery_form.cleaned_data.get('notes', '')
                    )

                    # Update claim and report status
                    claim.status = 'COMPLETED'
                    claim.save(update_fields=['status'])

                    claim.item_report.approval_status = 'ARCHIVED'
                    claim.item_report.is_publicly_visible = False
                    claim.item_report.save(update_fields=['approval_status', 'is_publicly_visible'])

                    # Notify claimant
                    Notification.objects.create(
                        recipient=claim.claimant,
                        title=f"Recovery Finalized: [{recovery.recovery_id}]",
                        message=f"Your item {claim.item_report.title} has been officially confirmed recovered and released to you.",
                        link=f"/claims/detail/{claim.claim_id}/",
                        notification_type='RECOVERY'
                    )

                    # Notify original finder if registered
                    Notification.objects.create(
                        recipient=claim.item_report.reporter,
                        title=f"Found Item Recovered!",
                        message=f"The item '{claim.item_report.title}' that you turned in has been successfully reunited with its verified owner. Thank you for making our campus safer!",
                        link=f"/items/report/{claim.item_report.report_id}/",
                        notification_type='RECOVERY'
                    )

                    AuditLog.objects.create(
                        actor=request.user,
                        action_type='RECOVERY_COMPLETED',
                        target_model='RecoveryRecord',
                        target_id=recovery.recovery_id,
                        details=f"Admin {request.user.username} completed recovery {recovery.recovery_id} for claim {claim.claim_id}",
                        ip_address=request.META.get('REMOTE_ADDR')
                    )

                    messages.success(request, f"Item recovery officially completed [{recovery.recovery_id}]. Records updated.")
                    return redirect('dashboard:recoveries_list')

    return render(request, 'dashboard/claim_inspect.html', {
        'claim': claim,
        'review_form': review_form,
        'recovery_form': recovery_form,
    })


@admin_required
def admin_recoveries_list_view(request):
    """View official recovery completion records."""
    recoveries = RecoveryRecord.objects.select_related(
        'found_report', 'recovered_by', 'admin', 'claim'
    ).order_by('-completed_at')

    paginator = Paginator(recoveries, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/recoveries_list.html', {'page_obj': page_obj})


@admin_required
def admin_contact_logs_view(request):
    """View administrative contact logs history."""
    logs = AdminContactLog.objects.select_related(
        'admin', 'contact_target', 'report', 'match'
    ).order_by('-created_at')

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/contact_logs_list.html', {'page_obj': page_obj})


@admin_required
def admin_audit_logs_view(request):
    """System-wide administrative audit trail."""
    logs = AuditLog.objects.select_related('actor').order_by('-created_at')

    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action_type=action_filter)

    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/audit_logs.html', {
        'page_obj': page_obj,
        'action_filter': action_filter or 'ALL',
    })
