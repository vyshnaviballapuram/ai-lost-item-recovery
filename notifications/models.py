from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    In-app database-backed notification for students and administrators.
    """
    NOTIFICATION_TYPES = (
        ('SUBMISSION', 'Report Submitted'),
        ('APPROVAL', 'Report Approved'),
        ('REJECTION', 'Report Rejected'),
        ('NEEDS_INFO', 'Information Requested'),
        ('MATCH_FOUND', 'Potential Match Found'),
        ('CONTACT', 'Admin Follow-up'),
        ('CLAIM_UPDATE', 'Claim Status Update'),
        ('RECOVERY', 'Item Recovery Completed'),
        ('SYSTEM', 'System Alert'),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, help_text="Internal URL for user action")
    notification_type = models.CharField(
        max_length=25,
        choices=NOTIFICATION_TYPES,
        default='SYSTEM',
        db_index=True
    )
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']

    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"[{status}] To {self.recipient.username}: {self.title}"
