from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'student_id', 'is_verified', 'is_staff')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'student_id', 'first_name', 'last_name')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Campus Information', {
            'fields': ('role', 'student_id', 'phone_number', 'department', 'avatar', 'is_verified')
        }),
    )
