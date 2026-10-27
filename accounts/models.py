from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model supporting Students, Campus Staff, and Administrators.
    """
    ROLE_CHOICES = (
        ('STUDENT', 'Student / Campus Member'),
        ('STAFF', 'Campus Staff / Security'),
        ('ADMIN', 'Campus Administrator'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='STUDENT',
        help_text="User authorization role on campus"
    )
    student_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Campus Roll Number or Staff ID"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Private contact telephone number"
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        help_text="Academic Department, School or Administrative Unit"
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        help_text="Optional profile photo"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="True if student/staff identity has been verified by administration"
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        full = self.get_full_name()
        return f"{full} ({self.username})" if full else self.username

    @property
    def is_admin_or_staff(self):
        """Check if user has administrative access to custom admin dashboard."""
        return self.is_superuser or self.is_staff or self.role in ('ADMIN', 'STAFF')

    @property
    def display_role(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)
