from django.contrib import admin
from .models import Category, ItemReport, ReportImage, ItemMatch, ReportReview, AdminContactLog, AuditLog


class ReportImageInline(admin.TabularInline):
    model = ReportImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ItemReport)
class ItemReportAdmin(admin.ModelAdmin):
    list_display = ('report_id', 'title', 'report_type', 'category', 'approval_status', 'is_publicly_visible', 'date_occurred', 'created_at')
    list_filter = ('report_type', 'approval_status', 'is_publicly_visible', 'category', 'date_occurred')
    search_fields = ('report_id', 'title', 'description', 'location_name', 'reporter__username')
    readonly_fields = ('report_id', 'created_at', 'updated_at')
    inlines = [ReportImageInline]


@admin.register(ItemMatch)
class ItemMatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'lost_report', 'found_report', 'similarity_score', 'status', 'is_active', 'created_at')
    list_filter = ('status', 'is_active')
    search_fields = ('lost_report__report_id', 'found_report__report_id')


@admin.register(ReportReview)
class ReportReviewAdmin(admin.ModelAdmin):
    list_display = ('report', 'reviewer', 'previous_status', 'new_status', 'action', 'created_at')
    list_filter = ('action',)


@admin.register(AdminContactLog)
class AdminContactLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'contact_target', 'contact_method', 'outcome', 'response_received', 'created_at')
    list_filter = ('contact_method', 'outcome', 'response_received')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor', 'action_type', 'target_model', 'target_id')
    list_filter = ('action_type', 'target_model')
    search_fields = ('target_id', 'details', 'actor__username')
    readonly_fields = ('created_at',)
