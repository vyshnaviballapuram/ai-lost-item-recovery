from django import forms
from django.utils import timezone
from .models import ItemReport, Category, AdminContactLog, ItemMatch


class ItemReportSubmissionForm(forms.ModelForm):
    """
    Submission form for students reporting Lost or Found items.
    Enforces privacy by clarifying that distinctive marks are private.
    """
    primary_photo = forms.ImageField(
        required=False,
        label="Primary Photograph",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )
    secondary_photo = forms.ImageField(
        required=False,
        label="Secondary / Detail Photograph (Optional)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )

    class Meta:
        model = ItemReport
        fields = [
            'report_type',
            'title',
            'category',
            'subcategory',
            'description',
            'distinctive_marks',
            'date_occurred',
            'time_occurred',
            'location_name',
            'location_details',
            'contact_phone',
            'contact_email',
            'contact_preference',
        ]
        widgets = {
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Midnight Blue Dell XPS 15 Laptop'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'subcategory': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Laptop, Wireless Earbuds, ID Badge'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide general observable details: color, approximate size, condition, stickers...'
            }),
            'distinctive_marks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'CONFIDENTIAL: Serial numbers, engraving, lock screen wallpaper, specific internal cards. Kept strictly private from public view.'
            }),
            'date_occurred': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time_occurred': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'location_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Central Library 2nd Floor, Engineering Block C, Main Cafeteria'
            }),
            'location_details': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Specific desk, bench, room 302, locker, bus stop...'
            }),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (555) 000-0000'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contact@campus.edu'}),
            'contact_preference': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_date_occurred(self):
        d = self.cleaned_data.get('date_occurred')
        if d and d > timezone.now().date():
            raise forms.ValidationError("The incident date cannot be in the future.")
        return d


class AdminReportReviewForm(forms.Form):
    """Administrator action form to approve, reject, or request information on a report."""
    ACTION_CHOICES = (
        ('APPROVE', 'Approve & Verify (Publish to public listings)'),
        ('NEEDS_INFORMATION', 'Request Additional Information from Reporter'),
        ('REJECT', 'Reject Report (Inappropriate or Duplicate)'),
        ('ARCHIVED', 'Archive Report'),
    )

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select fw-semibold'})
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for rejection or specific clarification questions requested from the student...'
        }),
        label="Decision Reason / Questions for Reporter"
    )
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Internal staff notes (never shown to student)...'
        }),
        label="Internal Staff Notes"
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        reason = cleaned_data.get('reason', '').strip()

        if action in ('REJECT', 'NEEDS_INFORMATION') and not reason:
            self.add_error('reason', f"A reason is required when choosing '{dict(self.ACTION_CHOICES).get(action)}'.")

        return cleaned_data


class AdminContactLogForm(forms.ModelForm):
    """Log an administrator contact attempt with a reporter."""
    class Meta:
        model = AdminContactLog
        fields = [
            'contact_target',
            'contact_method',
            'contact_details_used',
            'response_received',
            'outcome',
            'notes',
            'follow_up_date'
        ]
        widgets = {
            'contact_target': forms.Select(attrs={'class': 'form-select'}),
            'contact_method': forms.Select(attrs={'class': 'form-select'}),
            'contact_details_used': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number dialed or email used'}),
            'response_received': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'outcome': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Discussion summary, confirmation of details, discrepancies observed...'}),
            'follow_up_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
