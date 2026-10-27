import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.Model):
    """Category classification for lost and found items."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default='bi-box-seam', help_text="Bootstrap icon class")
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class ItemReport(models.Model):
    """
    Core item report model for Lost or Found items.
    CRITICAL: Reports default to PENDING status and NEVER appear publicly without Admin approval.
    """
    REPORT_TYPES = (
        ('LOST', 'Lost Item'),
        ('FOUND', 'Found Item'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pending Admin Review'),
        ('NEEDS_INFORMATION', 'Needs Additional Information'),
        ('APPROVED', 'Approved & Verified'),
        ('REJECTED', 'Rejected'),
        ('ARCHIVED', 'Archived / Recovered'),
    )

    report_id = models.CharField(max_length=32, unique=True, editable=False, db_index=True)
    report_type = models.CharField(max_length=10, choices=REPORT_TYPES, db_index=True)
    title = models.CharField(max_length=200, help_text="Brief item title")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='reports')
    subcategory = models.CharField(max_length=100, blank=True, help_text="e.g., iPhone 13, Leather Wallet, ID Card")
    description = models.TextField(help_text="Detailed description of the item")
    distinctive_marks = models.TextField(
        blank=True,
        help_text="Confidential: serial numbers, distinctive stickers, case color, wallpapers, lock screens, internal markings used for verification."
    )
    date_occurred = models.DateField(help_text="Date lost or found")
    time_occurred = models.TimeField(blank=True, null=True, help_text="Approximate time")
    location_name = models.CharField(
        max_length=200,
        help_text="Campus area (e.g. Central Library 2nd Floor, Engineering Block C, Main Cafeteria)"
    )
    location_details = models.TextField(
        blank=True,
        help_text="Specific desk, bench, room number, or locker details"
    )

    # Reporter & Contact Information (Private)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports')
    contact_phone = models.CharField(max_length=20, blank=True, help_text="Private contact telephone number")
    contact_email = models.EmailField(blank=True, help_text="Private contact email address")
    contact_preference = models.CharField(
        max_length=20,
        choices=(
            ('EMAIL', 'Email'),
            ('PHONE', 'Phone'),
            ('IN_APP', 'Campus Notification Only'),
        ),
        default='EMAIL'
    )

    # Admin Approval Workflow
    approval_status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )
    rejection_reason = models.TextField(blank=True, help_text="Admin rationale if rejected or if more info is needed")
    admin_notes = models.TextField(blank=True, help_text="Internal confidential notes visible only to administrators")
    is_publicly_visible = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True ONLY when approved AND permitted by campus visibility policy"
    )

    # AI Processing State
    ai_processed = models.BooleanField(default=False, help_text="Has AI matching engine evaluated this report?")
    ai_processing_error = models.TextField(blank=True, help_text="Recorded error if AI evaluation failed")

    # Audit & Review Timestamps
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_reports'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Item Report'
        verbose_name_plural = 'Item Reports'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.report_id:
            prefix = "LOST" if self.report_type == 'LOST' else "FND"
            token = uuid.uuid4().hex[:6].upper()
            date_str = timezone.now().strftime("%Y%m%d")
            self.report_id = f"{prefix}-{date_str}-{token}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.report_id}] {self.title} ({self.get_approval_status_display()})"

    @property
    def primary_image(self):
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary
        return self.images.first()

    @property
    def is_approved(self):
        return self.approval_status == 'APPROVED'

    def can_transition_to(self, target_status):
        """Validate state machine transitions."""
        valid_transitions = {
            'PENDING': ['APPROVED', 'REJECTED', 'NEEDS_INFORMATION'],
            'NEEDS_INFORMATION': ['APPROVED', 'REJECTED', 'PENDING'],
            'APPROVED': ['ARCHIVED', 'REJECTED', 'NEEDS_INFORMATION'],
            'REJECTED': ['ARCHIVED', 'PENDING'],
            'ARCHIVED': ['PENDING'],
        }
        return target_status in valid_transitions.get(self.approval_status, [])


class ReportImage(models.Model):
    """Photographs uploaded by the reporter for item verification."""
    report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='item_photos/')
    is_primary = models.BooleanField(default=False)
    caption = models.CharField(max_length=150, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Report Image'
        verbose_name_plural = 'Report Images'
        ordering = ['-is_primary', 'uploaded_at']

    def __str__(self):
        return f"Photo for {self.report.report_id}"


class ItemMatch(models.Model):
    """
    AI-generated match pair between a LOST report and a FOUND report.
    Never matches LOST with LOST, or FOUND with FOUND.
    """
    MATCH_STATUS_CHOICES = (
        ('PENDING_REVIEW', 'Pending Admin Review'),
        ('UNDER_REVIEW', 'Under Admin Investigation'),
        ('VERIFIED_MATCH', 'Verified Compatible Match'),
        ('DISMISSED', 'Dismissed / Incompatible'),
    )

    lost_report = models.ForeignKey(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='matches_as_lost',
        limit_choices_to={'report_type': 'LOST'}
    )
    found_report = models.ForeignKey(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='matches_as_found',
        limit_choices_to={'report_type': 'FOUND'}
    )
    similarity_score = models.FloatField(help_text="Composite similarity score (0.0 to 100.0)")
    text_similarity = models.FloatField(default=0.0, help_text="TF-IDF Text & Title similarity score (0-100)")
    category_similarity = models.FloatField(default=0.0, help_text="Category & subcategory compatibility (0-100)")
    attribute_similarity = models.FloatField(default=0.0, help_text="Distinctive marks & token overlap (0-100)")
    location_similarity = models.FloatField(default=0.0, help_text="Campus zone & location proximity (0-100)")
    date_similarity = models.FloatField(default=0.0, help_text="Temporal timeline coherence (0-100)")

    matching_reasons = models.JSONField(
        default=list,
        help_text="List of human-readable matching justification strings generated by AI engine"
    )
    status = models.CharField(
        max_length=25,
        choices=MATCH_STATUS_CHOICES,
        default='PENDING_REVIEW',
        db_index=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    admin_notes = models.TextField(blank=True, help_text="Administrator match inspection notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'AI Item Match'
        verbose_name_plural = 'AI Item Matches'
        ordering = ['-similarity_score', '-created_at']
        constraints = [
            models.UniqueConstraint(fields=['lost_report', 'found_report'], name='unique_lost_found_match_pair')
        ]

    def __str__(self):
        return f"Match: {self.lost_report.report_id} <-> {self.found_report.report_id} ({self.similarity_score:.1f}%)"


class ReportReview(models.Model):
    """Historical audit of report approval / rejection actions taken by administrators."""
    report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    previous_status = models.CharField(max_length=25)
    new_status = models.CharField(max_length=25)
    action = models.CharField(max_length=30)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.report.report_id} transition from {self.previous_status} to {self.new_status}"


class AdminContactLog(models.Model):
    """
    Log of administrative contact attempts with students/reporters
    to verify item details or match compatibility.
    """
    CONTACT_METHODS = (
        ('EMAIL', 'Campus Email'),
        ('PHONE', 'Phone Call'),
        ('SMS', 'SMS Text'),
        ('IN_PERSON', 'In-Person Desk / Help Center'),
        ('IN_APP', 'Campus Notification'),
    )

    OUTCOMES = (
        ('AWAITING_REPLY', 'Awaiting Student Response'),
        ('CONFIRMED_CONSISTENT', 'Details Confirmed Consistent'),
        ('INCONSISTENT', 'Details Contradictory / Not A Match'),
        ('UNREACHABLE', 'Student Unreachable'),
        ('RESOLVED', 'Contact Completed'),
    )

    report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='contact_logs', null=True, blank=True)
    match = models.ForeignKey(ItemMatch, on_delete=models.CASCADE, related_name='contact_logs', null=True, blank=True)
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='admin_contacts_made')
    contact_target = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contact_logs_received')
    contact_method = models.CharField(max_length=20, choices=CONTACT_METHODS, default='EMAIL')
    contact_details_used = models.CharField(max_length=150, help_text="Email address or phone dialed")
    response_received = models.BooleanField(default=False)
    outcome = models.CharField(max_length=30, choices=OUTCOMES, default='AWAITING_REPLY')
    notes = models.TextField(help_text="Verification findings, questions asked, response details")
    follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Contact {self.contact_target.username} via {self.contact_method} by {self.admin}"


class AuditLog(models.Model):
    """System-wide security and operations audit log."""
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.CharField(max_length=50, db_index=True)
    target_model = models.CharField(max_length=50)
    target_id = models.CharField(max_length=50)
    details = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {self.action_type} on {self.target_model}:{self.target_id}"
