import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from items.models import Category, ItemReport


class ItemReportWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Electronics", slug="electronics")

        self.student_a = User.objects.create_user(
            username='student_a', password='Password123!', email='a@campus.edu'
        )
        self.student_b = User.objects.create_user(
            username='student_b', password='Password123!', email='b@campus.edu'
        )
        self.admin_user = User.objects.create_user(
            username='admin_staff', password='Password123!', email='admin@campus.edu',
            role='ADMIN', is_staff=True
        )

    def test_report_creation_and_pending_status(self):
        """CRITICAL: Submitting report must default to PENDING and NOT be public."""
        self.client.login(username='student_a', password='Password123!')
        response = self.client.post(reverse('items:report_lost'), {
            'report_type': 'LOST',
            'title': 'Space Gray MacBook Air M2',
            'category': self.category.id,
            'subcategory': 'Laptop',
            'description': 'Left on table in cafeteria.',
            'distinctive_marks': 'Serial C02XXXX, Sticker of Python logo',
            'date_occurred': timezone.now().date(),
            'location_name': 'Student Cafeteria',
            'contact_phone': '+1-555-1234',
            'contact_email': 'a@campus.edu',
            'contact_preference': 'EMAIL'
        })
        self.assertEqual(response.status_code, 302)

        report = ItemReport.objects.get(title='Space Gray MacBook Air M2')
        self.assertEqual(report.approval_status, 'PENDING')
        self.assertFalse(report.is_publicly_visible)
        self.assertEqual(report.reporter, self.student_a)
        self.assertTrue(report.report_id.startswith('LOST-'))

    def test_pending_and_rejected_reports_hidden_from_public_listings(self):
        """Public listings must NEVER display PENDING, REJECTED or ARCHIVED reports."""
        today = timezone.now().date()
        # Pending report
        pending_rep = ItemReport.objects.create(
            report_type='LOST', title='Pending Item Hidden', category=self.category,
            description='Test pending', date_occurred=today, location_name='Library',
            reporter=self.student_a, approval_status='PENDING', is_publicly_visible=False
        )
        # Rejected report
        rejected_rep = ItemReport.objects.create(
            report_type='LOST', title='Rejected Item Hidden', category=self.category,
            description='Test rejected', date_occurred=today, location_name='Library',
            reporter=self.student_a, approval_status='REJECTED', is_publicly_visible=False
        )
        # Approved report
        approved_rep = ItemReport.objects.create(
            report_type='FOUND', title='Approved Public Item', category=self.category,
            description='Test approved', date_occurred=today, location_name='Library',
            reporter=self.student_b, approval_status='APPROVED', is_publicly_visible=True
        )

        response = self.client.get(reverse('items:public_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        self.assertIn('Approved Public Item', content)
        self.assertNotIn('Pending Item Hidden', content)
        self.assertNotIn('Rejected Item Hidden', content)

    def test_idor_protection_for_private_reports(self):
        """Unauthorized students cannot access another student's unapproved report directly by URL."""
        today = timezone.now().date()
        pending_rep = ItemReport.objects.create(
            report_type='LOST', title='Secret Private Pending Item', category=self.category,
            description='Test private', date_occurred=today, location_name='Library',
            reporter=self.student_a, approval_status='PENDING', is_publicly_visible=False
        )

        # Anonymous request -> 404
        response_anon = self.client.get(reverse('items:report_detail', args=[pending_rep.report_id]))
        self.assertEqual(response_anon.status_code, 404)

        # Student B request -> 404
        self.client.login(username='student_b', password='Password123!')
        response_b = self.client.get(reverse('items:report_detail', args=[pending_rep.report_id]))
        self.assertEqual(response_b.status_code, 404)

        # Student A (Owner) request -> 200
        self.client.login(username='student_a', password='Password123!')
        response_a = self.client.get(reverse('items:report_detail', args=[pending_rep.report_id]))
        self.assertEqual(response_a.status_code, 200)

        # Admin Staff request -> 200
        self.client.login(username='admin_staff', password='Password123!')
        response_admin = self.client.get(reverse('items:report_detail', args=[pending_rep.report_id]))
        self.assertEqual(response_admin.status_code, 200)
