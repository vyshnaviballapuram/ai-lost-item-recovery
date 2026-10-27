import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from items.models import ItemReport


class OwnershipClaim(models.Model):
    """
    Formal claim submitted by a student asserting ownership over a reported found item.
    Admin reviews claimant evidence against confidential item markings.
    """
    CLAIM_STATUSES = (
        ('PENDING_REVIEW', 'Pending Admin Review'),
        ('NEEDS_INFORMATION', 'Needs Additional Evidence'),
        ('VERIFIED', 'Verified / Ownership Established'),
        ('REJECTED', 'Claim Rejected'),
        ('COMPLETED', 'Item Returned & Recovered'),
    )

    claim_id = models.CharField(max_length=32, unique=True, editable=False, db_index=True)
    item_report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='claims')
    claimant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='claims')
    evidence_description = models.TextField(
        help_text="Detailed ownership evidence: private markings, serial numbers, password patterns, purchase dates, receipts."
    )
    proof_file = models.FileField(
        upload_to='claim_proofs/',
        blank=True,
        null=True,
        help_text="Optional receipt, warranty card, invoice or previous photo showing item."
    )
    contact_phone = models.CharField(max_length=20, help_text="Direct contact phone number")
    contact_email = models.EmailField(help_text="Direct contact email address")
    status = models.CharField(
        max_length=25,
        choices=CLAIM_STATUSES,
        default='PENDING_REVIEW',
        db_index=True
    )
    admin_notes = models.TextField(blank=True, help_text="Confidential verification rationale and notes")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_claims'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ownership Claim'
        verbose_name_plural = 'Ownership Claims'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.claim_id:
            token = uuid.uuid4().hex[:6].upper()
            date_str = timezone.now().strftime("%Y%m%d")
            self.claim_id = f"CLM-{date_str}-{token}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.claim_id}] Claim by {self.claimant.username} on {self.item_report.report_id}"


class RecoveryRecord(models.Model):
    """
    Official audit record created when an item is officially recovered and returned to its rightful owner.
    """
    recovery_id = models.CharField(max_length=32, unique=True, editable=False, db_index=True)
    lost_report = models.ForeignKey(
        ItemReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recovery_as_lost'
    )
    found_report = models.ForeignKey(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='recovery_as_found'
    )
    claim = models.ForeignKey(
        OwnershipClaim,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recovery_record'
    )
    recovered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recovered_items',
        help_text="Student / owner who received the item"
    )
    returned_by_name = models.CharField(
        max_length=150,
        help_text="Finder name or department officer (e.g. Campus Security Desk, Student Help Center)"
    )
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='verified_recoveries',
        help_text="Staff officer who supervised hand-off"
    )
    verification_summary = models.TextField(
        help_text="Summary of how identity was confirmed and item released."
    )
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Recovery Record'
        verbose_name_plural = 'Recovery Records'
        ordering = ['-completed_at']

    def save(self, *args, **kwargs):
        if not self.recovery_id:
            token = uuid.uuid4().hex[:6].upper()
            date_str = timezone.now().strftime("%Y%m%d")
            self.recovery_id = f"REC-{date_str}-{token}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.recovery_id}] Item {self.found_report.report_id} recovered by {self.recovered_by.username}"
