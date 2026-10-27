from django import forms
from .models import OwnershipClaim, RecoveryRecord


class OwnershipClaimForm(forms.ModelForm):
    """Student submission form to claim ownership over a found item."""
    class Meta:
        model = OwnershipClaim
        fields = ['evidence_description', 'proof_file', 'contact_phone', 'contact_email']
        widgets = {
            'evidence_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide specific proof only the owner would know: serial number, passwords, wallpaper description, stickers, purchase receipts, or scratches...'
            }),
            'proof_file': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (555) 000-0000'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'student@campus.edu'}),
        }


class AdminClaimReviewForm(forms.ModelForm):
    """Admin review decision form for ownership claims."""
    class Meta:
        model = OwnershipClaim
        fields = ['status', 'admin_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select fw-semibold'}),
            'admin_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Verification rationale, documentation checked, interview notes...'
            }),
        }


class RecoveryCompletionForm(forms.Form):
    """Final hand-off confirmation form executed only by campus administrators."""
    returned_by_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Officer Davis (Security Desk) or Campus Help Center'}),
        label="Custodian / Returning Officer"
    )
    verification_summary = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Document how physical identity was confirmed: Student ID inspected, item unlocked with passcode, signature received...'
        }),
        label="Verification and Hand-over Summary"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Additional administrative remarks...'}),
        label="Closing Notes (Optional)"
    )
