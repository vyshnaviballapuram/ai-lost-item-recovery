"""
Workflow orchestrator for report submission, admin approval, and lifecycle state management.
"""

import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from items.models import ItemReport, ReportImage, ReportReview, AuditLog
from notifications.models import Notification
from accounts.models import User
from .ai_matching import run_ai_matching_for_report, deactivate_matches_for_report

logger = logging.getLogger(__name__)


def submit_item_report(reporter, report_data, image_files=None, request_ip=None):
    """
    Submits a new item report.
    CRITICAL: Always initializes with PENDING status. NEVER publishes publicly immediately.
    """
    with transaction.atomic():
        report = ItemReport.objects.create(
            report_type=report_data['report_type'],
            title=report_data['title'],
            category=report_data['category'],
            subcategory=report_data.get('subcategory', ''),
            description=report_data['description'],
            distinctive_marks=report_data.get('distinctive_marks', ''),
            date_occurred=report_data['date_occurred'],
            time_occurred=report_data.get('time_occurred'),
            location_name=report_data['location_name'],
            location_details=report_data.get('location_details', ''),
            reporter=reporter,
            contact_phone=report_data.get('contact_phone', reporter.phone_number),
            contact_email=report_data.get('contact_email', reporter.email),
            contact_preference=report_data.get('contact_preference', 'EMAIL'),
            approval_status='PENDING',
            is_publicly_visible=False,
            ai_processed=False
        )

        # Save images
        if image_files:
            for idx, img_file in enumerate(image_files):
                ReportImage.objects.create(
                    report=report,
                    image=img_file,
                    is_primary=(idx == 0)
                )

        # Log audit entry
        AuditLog.objects.create(
            actor=reporter,
            action_type='REPORT_SUBMITTED',
            target_model='ItemReport',
            target_id=report.report_id,
            details=f"User {reporter.username} submitted {report.report_type} report: {report.title} (Status: PENDING)",
            ip_address=request_ip
        )

        # Notify reporter
        Notification.objects.create(
            recipient=reporter,
            title=f"Report Submitted: {report.title}",
            message=(
                f"Your {report.get_report_type_display().lower()} report [{report.report_id}] has been securely received "
                f"and is currently pending administrator verification. You will be notified once reviewed."
            ),
            link=f"/items/report/{report.report_id}/",
            notification_type='SUBMISSION'
        )

        # Notify active administrators of incoming pending report
        admins = User.objects.filter(models_Q_admin())
        for adm in admins:
            Notification.objects.create(
                recipient=adm,
                title=f"New {report.get_report_type_display()} Pending Approval",
                message=f"Report [{report.report_id}] '{report.title}' by {reporter.username} requires review.",
                link=f"/admin-dashboard/reports/{report.report_id}/",
                notification_type='SUBMISSION'
            )

    # Trigger AI matching (runs outside atomic block or safely after commit)
    try:
        run_ai_matching_for_report(report)
    except Exception as e:
        logger.error(f"Error executing AI matching after report submission {report.report_id}: {e}")

    return report


def update_report_approval(report, admin_user, new_status, reason="", notes="", request_ip=None):
    """
    Execute administrator approval transition with strict validation, state recording, and notification.
    """
    old_status = report.approval_status
    if not report.can_transition_to(new_status):
        raise ValueError(f"Illegal state transition from {old_status} to {new_status}")

    with transaction.atomic():
        report.approval_status = new_status
        report.reviewed_by = admin_user
        report.reviewed_at = timezone.now()

        if notes:
            report.admin_notes = f"{report.admin_notes}\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {admin_user.username}: {notes}".strip()

        if new_status == 'APPROVED':
            # Only approved reports are eligible for public listing
            report.is_publicly_visible = getattr(settings, 'PUBLIC_REPORTS_ENABLED', True)
            report.rejection_reason = ""
            notif_type = 'APPROVAL'
            notif_title = f"Report Approved: {report.title}"
            notif_msg = (
                f"Your report [{report.report_id}] has been verified and approved by campus administration. "
                f"It is now active in recovery matching."
            )
        elif new_status == 'REJECTED':
            report.is_publicly_visible = False
            report.rejection_reason = reason
            deactivate_matches_for_report(report)
            notif_type = 'REJECTION'
            notif_title = f"Report Rejected: {report.title}"
            notif_msg = (
                f"Your report [{report.report_id}] was not approved. Reason: {reason or 'Did not meet campus guidelines'}"
            )
        elif new_status == 'NEEDS_INFORMATION':
            report.is_publicly_visible = False
            report.rejection_reason = reason
            notif_type = 'NEEDS_INFO'
            notif_title = f"Action Required: Information Requested for [{report.report_id}]"
            notif_msg = (
                f"The campus administrator requires additional clarification for your report: {reason}"
            )
        elif new_status == 'ARCHIVED':
            report.is_publicly_visible = False
            deactivate_matches_for_report(report)
            notif_type = 'SYSTEM'
            notif_title = f"Report Archived: [{report.report_id}]"
            notif_msg = f"Your report [{report.report_id}] has been closed and archived."
        else:
            report.is_publicly_visible = False
            notif_type = 'SYSTEM'
            notif_title = f"Status Update: [{report.report_id}]"
            notif_msg = f"Your report status has changed to {report.get_approval_status_display()}."

        report.save()

        # Record Review History
        ReportReview.objects.create(
            report=report,
            reviewer=admin_user,
            previous_status=old_status,
            new_status=new_status,
            action=new_status,
            reason=reason or notes
        )

        # Audit Log
        AuditLog.objects.create(
            actor=admin_user,
            action_type=f'REPORT_{new_status}',
            target_model='ItemReport',
            target_id=report.report_id,
            details=f"Admin {admin_user.username} changed status from {old_status} to {new_status}. Reason: {reason}",
            ip_address=request_ip
        )

        # Notify Reporter
        Notification.objects.create(
            recipient=report.reporter,
            title=notif_title,
            message=notif_msg,
            link=f"/items/report/{report.report_id}/",
            notification_type=notif_type
        )

    return report


def models_Q_admin():
    from django.db.models import Q
    return Q(is_superuser=True) | Q(is_staff=True) | Q(role__in=['ADMIN', 'STAFF'])
