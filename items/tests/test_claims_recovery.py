from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from items.models import Category, ItemReport
from claims.models import OwnershipClaim, RecoveryRecord
from notifications.models import Notification


class OwnershipClaimsAndRecoveryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Electronics", slug="electronics")

        self.finder = User.objects.create_user(username='finder_user', password='Password123!', email='finder@campus.edu')
        self.owner = User.objects.create_user(username='owner_user', password='Password123!', email='owner@campus.edu')
        self.admin = User.objects.create_user(username='admin_boss', password='Password123!', email='boss@campus.edu', role='ADMIN', is_staff=True)

        self.found_item = ItemReport.objects.create(
            report_type='FOUND',
            title='Found Sony Wireless Headphones',
            category=self.category,
            description='Black over-ear headphones found in auditorium.',
            distinctive_marks='Custom anime sticker on right earcup; initials S.K.',
            date_occurred=timezone.now().date(),
            location_name='Main Auditorium',
            reporter=self.finder,
            approval_status='APPROVED',
            is_publicly_visible=True
        )

    def test_claim_submission(self):
        """Owner can submit an ownership claim with evidence."""
        self.client.login(username='owner_user', password='Password123!')
        response = self.client.post(reverse('claims:submit_claim', args=[self.found_item.report_id]), {
            'evidence_description': 'Has custom anime sticker on right earcup; initials S.K. engraved on inner headband.',
            'contact_phone': '+1-555-9090',
            'contact_email': 'owner@campus.edu'
        })
        self.assertEqual(response.status_code, 302)

        claim = OwnershipClaim.objects.get(item_report=self.found_item, claimant=self.owner)
        self.assertEqual(claim.status, 'PENDING_REVIEW')
        self.assertTrue(claim.claim_id.startswith('CLM-'))

    def test_finder_cannot_claim_own_found_item(self):
        """A user cannot submit an ownership claim against their own submitted item."""
        self.client.login(username='finder_user', password='Password123!')
        response = self.client.post(reverse('claims:submit_claim', args=[self.found_item.report_id]), {
            'evidence_description': 'Trying to claim own report',
            'contact_phone': '+1-555-0000',
            'contact_email': 'finder@campus.edu'
        })
        self.assertEqual(response.status_code, 302)
        # Verify no claim created
        self.assertEqual(OwnershipClaim.objects.filter(claimant=self.finder).count(), 0)

    def test_recovery_finalization_workflow(self):
        """Finalizing recovery creates RecoveryRecord, marks claim COMPLETED, and archives report."""
        claim = OwnershipClaim.objects.create(
            item_report=self.found_item,
            claimant=self.owner,
            evidence_description="Initials S.K. on inner headband.",
            contact_phone='+1-555-9090',
            contact_email='owner@campus.edu',
            status='VERIFIED'
        )

        self.client.login(username='admin_boss', password='Password123!')
        response = self.client.post(reverse('dashboard:claim_inspect', args=[claim.claim_id]), {
            'form_type': 'finalize_recovery',
            'returned_by_name': 'Campus Security Officer Miller',
            'verification_summary': 'Owner S.K. presented student roll card CS-2023-011 and unlocked audio app pairing.',
            'notes': 'Item hand-off completed smoothly.'
        })
        self.assertEqual(response.status_code, 302)

        claim.refresh_from_db()
        self.found_item.refresh_from_db()

        self.assertEqual(claim.status, 'COMPLETED')
        self.assertEqual(self.found_item.approval_status, 'ARCHIVED')
        self.assertFalse(self.found_item.is_publicly_visible)

        # RecoveryRecord exists
        recovery = RecoveryRecord.objects.get(claim=claim)
        self.assertEqual(recovery.recovered_by, self.owner)
        self.assertEqual(recovery.admin, self.admin)
        self.assertTrue(recovery.recovery_id.startswith('REC-'))

        # Both claimant and finder received completion notifications
        owner_notif = Notification.objects.filter(recipient=self.owner, notification_type='RECOVERY').first()
        finder_notif = Notification.objects.filter(recipient=self.finder, notification_type='RECOVERY').first()
        self.assertIsNotNone(owner_notif)
        self.assertIsNotNone(finder_notif)
