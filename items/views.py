from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from .models import ItemReport, Category, ReportImage, ItemMatch
from .forms import ItemReportSubmissionForm
from .services.report_workflow import submit_item_report


@login_required
def report_submit_view(request, report_type='LOST'):
    """
    Submit a new Lost or Found item report.
    CRITICAL: The report always receives PENDING approval status and is NEVER displayed publicly automatically.
    """
    initial_type = 'LOST' if report_type.upper() == 'LOST' else 'FOUND'

    if request.method == 'POST':
        form = ItemReportSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            report_data = form.cleaned_data
            primary_file = form.cleaned_data.get('primary_photo')
            secondary_file = form.cleaned_data.get('secondary_photo')

            image_files = []
            if primary_file:
                image_files.append(primary_file)
            if secondary_file:
                image_files.append(secondary_file)

            report = submit_item_report(
                reporter=request.user,
                report_data=report_data,
                image_files=image_files,
                request_ip=request.META.get('REMOTE_ADDR')
            )

            messages.success(
                request,
                f"Your {report.get_report_type_display().lower()} report [{report.report_id}] was submitted successfully! "
                f"Status: PENDING ADMIN REVIEW. It will be verified by campus administration before publication."
            )
            return redirect('items:report_detail', report_id=report.report_id)
        else:
            messages.error(request, "Please review and correct the errors below.")
    else:
        # Prepopulate with profile contact info
        form = ItemReportSubmissionForm(initial={
            'report_type': initial_type,
            'contact_phone': request.user.phone_number,
            'contact_email': request.user.email,
        })

    return render(request, 'items/report_form.html', {
        'form': form,
        'report_type': initial_type,
    })


def report_detail_view(request, report_id):
    """
    View report details.
    PRIVACY PROTECTION:
    - Unapproved reports (PENDING, REJECTED, NEEDS_INFO) are strictly restricted to the reporter and staff/admin.
    - Sensitive distinctive marks and confidential contact info are stripped for general viewers.
    """
    report = get_object_or_404(ItemReport, report_id=report_id)
    user = request.user

    is_owner = user.is_authenticated and report.reporter_id == user.id
    is_staff = user.is_authenticated and getattr(user, 'is_admin_or_staff', False)

    # Access Authorization Check for Non-Approved Reports
    if not report.is_approved:
        if not (is_owner or is_staff):
            raise Http404("This report is either pending administrative verification or does not exist.")

    # Determine whether sensitive details are viewable
    can_view_sensitive = is_owner or is_staff

    # Get associated active matches if admin
    admin_matches = None
    if is_staff:
        if report.report_type == 'LOST':
            admin_matches = report.matches_as_lost.filter(is_active=True).order_by('-similarity_score')
        else:
            admin_matches = report.matches_as_found.filter(is_active=True).order_by('-similarity_score')

    context = {
        'report': report,
        'is_owner': is_owner,
        'is_staff': is_staff,
        'can_view_sensitive': can_view_sensitive,
        'admin_matches': admin_matches,
        'reviews': report.reviews.all() if (is_owner or is_staff) else [],
        'contact_logs': report.contact_logs.all() if is_staff else [],
    }
    return render(request, 'items/report_detail.html', context)


@login_required
def report_edit_view(request, report_id):
    """Allow reporters to update details when additional information is requested."""
    report = get_object_or_404(ItemReport, report_id=report_id)

    # Permission check: only original reporter can edit
    if report.reporter != request.user and not getattr(request.user, 'is_admin_or_staff', False):
        raise PermissionDenied("You are not authorized to edit this report.")

    if request.method == 'POST':
        form = ItemReportSubmissionForm(request.POST, request.FILES, instance=report)
        if form.is_valid():
            updated_report = form.save(commit=False)
            # If was needing info, reset to PENDING for admin re-evaluation
            if updated_report.approval_status == 'NEEDS_INFORMATION':
                updated_report.approval_status = 'PENDING'
            updated_report.save()

            # Handle new photo uploads
            new_primary = form.cleaned_data.get('primary_photo')
            if new_primary:
                ReportImage.objects.create(report=updated_report, image=new_primary, is_primary=True)

            messages.success(request, f"Report [{report.report_id}] details have been updated.")
            return redirect('items:report_detail', report_id=report.report_id)
    else:
        form = ItemReportSubmissionForm(instance=report)

    return render(request, 'items/report_edit.html', {
        'form': form,
        'report': report,
    })


def approved_public_list_view(request):
    """
    Public listings page.
    STRICT SECURITY RULE: Only APPROVED reports marked is_publicly_visible=True are shown.
    Pending, rejected, or archived reports are NEVER exposed here.
    """
    # Base queryset: only approved and visible
    queryset = ItemReport.objects.filter(
        approval_status='APPROVED',
        is_publicly_visible=True
    ).select_related('category', 'reporter').prefetch_related('images')

    # Filters
    report_type = request.GET.get('type')
    if report_type in ('LOST', 'FOUND'):
        queryset = queryset.filter(report_type=report_type)

    category_slug = request.GET.get('category')
    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)

    search_query = request.GET.get('q', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location_name__icontains=search_query) |
            Q(subcategory__icontains=search_query)
        )

    # Ordering
    sort = request.GET.get('sort', '-date_occurred')
    if sort in ('-date_occurred', 'date_occurred', '-created_at'):
        queryset = queryset.order_by(sort)
    else:
        queryset = queryset.order_by('-date_occurred')

    # Pagination
    paginator = Paginator(queryset, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_type': report_type or 'ALL',
        'current_category': category_slug or '',
        'search_query': search_query,
        'total_count': queryset.count(),
    }
    return render(request, 'items/public_list.html', context)
