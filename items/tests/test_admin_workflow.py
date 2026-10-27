from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from items.models import Category, ItemReport, ItemMatch, AuditLog, AdminContactLog
from items.services.report_workflow import update_report_approval
from notifications.models import Notification


class AdminWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Keys", slug="keys")

        self.student = User.objects.create_user(
            username='student_user', password='Password123!', email='student@campus.edu'
        )
        self.admin = User.objects.create_user(
            username='admin_officer', password='Password123!', email='officer@campus.edu',
            role='ADMIN', is_staff=True
        )

        self.report = ItemReport.objects.create(
            report_type='LOST',
            title='Campus Key Ring with Red Tag',
            category=self.category,
            description='Lost near sports hall',
            date_occurred=timezone.now().date(),
            location_name='Sports Complex',
            reporter=self.student,
            approval_status='PENDING',
            is_publicly_visible=False
        )

    def test_unauthorized_user_denied_admin_access(self):
        """Regular students cannot access custom admin dashboard views (returns 403)."""
        self.client.login(username='student_user', password='Password123!')
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.status_code, 403)

        response_appr = self.client.get(reverse('dashboard:approvals'))
        self.assertEqual(response_appr.status_code, 403)

    def test_admin_approval_workflow(self):
        """Approving a report makes it public and notifies the reporter."""
        update_report_approval(
            report=self.report,
            admin_user=self.admin,
            new_status='APPROVED',
            notes="Details physically verified with security log."
        )

        self.report.refresh_from_db()
        self.assertEqual(self.report.approval_status, 'APPROVED')
        self.assertTrue(self.report.is_publicly_visible)
        self.assertEqual(self.report.reviewed_by, self.admin)

        # Notification verification
        notif = Notification.objects.filter(recipient=self.student, notification_type='APPROVAL').first()
        self.assertIsNotNone(notif)
        self.assertIn('approved', notif.message.lower())

        # Audit log verification
        audit = AuditLog.objects.filter(target_id=self.report.report_id, action_type='REPORT_APPROVED').first()
        self.assertIsNotNone(audit)

    def test_admin_rejection_workflow(self):
        """Rejecting a report records reason, keeps it hidden, and alerts reporter."""
        update_report_approval(
            report=self.report,
            admin_user=self.admin,
            new_status='REJECTED',
            reason="Item violates campus prohibited items policy."
        )

        self.report.refresh_from_db()
        self.assertEqual(self.report.approval_status, 'REJECTED')
        self.assertFalse(self.report.is_publicly_visible)
        self.assertIn("prohibited", self.report.rejection_reason)

        notif = Notification.objects.filter(recipient=self.student, notification_type='REJECTION').first()
        self.assertIsNotNone(notif)
        self.assertIn('prohibited', notif.message)

    def test_admin_contact_log_persistence(self):
        """Admin can log student verification contact attempts."""
        log = AdminContactLog.objects.create(
            report=self.report,
            admin=self.admin,
            contact_target=self.student,
            contact_method='PHONE',
            contact_details_used='+1-555-4321',
            response_received=True,
            outcome='CONFIRMED_CONSISTENT',
            notes='Student confirmed number of keys on ring.'
        )
        self.assertEqual(log.outcome, 'CONFIRMED_CONSISTENT')
        self.assertTrue(log.response_received)
