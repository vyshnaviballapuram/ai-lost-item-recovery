from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from items.models import ItemReport, AuditLog
from accounts.models import User
from notifications.models import Notification
from .models import OwnershipClaim, RecoveryRecord
from .forms import OwnershipClaimForm


@login_required
def submit_claim_view(request, report_id):
    """
    Submit ownership claim for an approved found item.
    Enforces that claimants must describe private distinguishing marks.
    """
    report = get_object_or_404(ItemReport, report_id=report_id)

    # Disallow claiming own report
    if report.reporter == request.user:
        messages.warning(request, "You cannot file an ownership claim against an item you reported yourself.")
        return redirect('items:report_detail', report_id=report.report_id)

    # Check for existing pending claim by this user
    existing_claim = OwnershipClaim.objects.filter(
        item_report=report,
        claimant=request.user
    ).exclude(status__in=['REJECTED', 'COMPLETED']).first()

    if existing_claim:
        messages.info(request, f"You already have an active claim [{existing_claim.claim_id}] pending for this item.")
        return redirect('claims:claim_detail', claim_id=existing_claim.claim_id)

    if request.method == 'POST':
        form = OwnershipClaimForm(request.POST, request.FILES)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.item_report = report
            claim.claimant = request.user
            claim.status = 'PENDING_REVIEW'
            claim.save()

            # Audit log
            AuditLog.objects.create(
                actor=request.user,
                action_type='CLAIM_SUBMITTED',
                target_model='OwnershipClaim',
                target_id=claim.claim_id,
                details=f"User {request.user.username} submitted ownership claim on report {report.report_id}",
                ip_address=request.META.get('REMOTE_ADDR')
            )

            # Notification to claimant
            Notification.objects.create(
                recipient=request.user,
                title=f"Ownership Claim Submitted: [{claim.claim_id}]",
                message=(
                    f"Your claim for item '{report.title}' [{report.report_id}] has been submitted. "
                    f"Campus administrators will verify your evidence against confidential item records."
                ),
                link=f"/claims/detail/{claim.claim_id}/",
                notification_type='CLAIM_UPDATE'
            )

            # Notify admins
            from items.services.report_workflow import models_Q_admin
            for adm in User.objects.filter(models_Q_admin()):
                Notification.objects.create(
                    recipient=adm,
                    title=f"New Ownership Claim: [{claim.claim_id}]",
                    message=f"Student {request.user.username} submitted a claim on found item [{report.report_id}].",
                    link=f"/admin-dashboard/claims/{claim.claim_id}/",
                    notification_type='CLAIM_UPDATE'
                )

            messages.success(
                request,
                f"Your claim [{claim.claim_id}] has been submitted and is under administrative review."
            )
            return redirect('claims:claim_detail', claim_id=claim.claim_id)
    else:
        form = OwnershipClaimForm(initial={
            'contact_phone': request.user.phone_number,
            'contact_email': request.user.email,
        })

    return render(request, 'claims/claim_form.html', {
        'form': form,
        'report': report,
    })


@login_required
def claim_detail_view(request, claim_id):
    """
    View claim details and verification status.
    Protected: Only claimant or campus staff/admin can view.
    """
    claim = get_object_or_404(OwnershipClaim, claim_id=claim_id)
    user = request.user

    is_claimant = claim.claimant == user
    is_staff = getattr(user, 'is_admin_or_staff', False)

    if not (is_claimant or is_staff):
        raise PermissionDenied("You are not authorized to view this claim.")

    return render(request, 'claims/claim_detail.html', {
        'claim': claim,
        'is_claimant': is_claimant,
        'is_staff': is_staff,
    })


@login_required
def my_claims_list_view(request):
    """List all ownership claims submitted by current user."""
    claims = OwnershipClaim.objects.filter(claimant=request.user).order_by('-created_at')
    return render(request, 'claims/my_claims.html', {'claims': claims})
