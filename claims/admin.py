from django.contrib import admin
from .models import OwnershipClaim, RecoveryRecord


@admin.register(OwnershipClaim)
class OwnershipClaimAdmin(admin.ModelAdmin):
    list_display = ('claim_id', 'item_report', 'claimant', 'status', 'reviewer', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('claim_id', 'claimant__username', 'item_report__report_id')


@admin.register(RecoveryRecord)
class RecoveryRecordAdmin(admin.ModelAdmin):
    list_display = ('recovery_id', 'found_report', 'recovered_by', 'admin', 'completed_at')
    search_fields = ('recovery_id', 'recovered_by__username', 'found_report__report_id')
