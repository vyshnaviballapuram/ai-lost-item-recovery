from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.admin_overview_view, name='overview'),
    path('approvals/', views.admin_approvals_view, name='approvals'),
    path('reports/<str:report_id>/', views.admin_report_inspect_view, name='report_inspect'),
    path('matches/', views.admin_matches_view, name='matches_list'),
    path('matches/<int:match_id>/status/', views.admin_update_match_status, name='update_match_status'),
    path('claims/', views.admin_claims_view, name='claims_list'),
    path('claims/<str:claim_id>/', views.admin_claim_inspect_view, name='claim_inspect'),
    path('recoveries/', views.admin_recoveries_list_view, name='recoveries_list'),
    path('contact-logs/', views.admin_contact_logs_view, name='contact_logs'),
    path('audit-logs/', views.admin_audit_logs_view, name='audit_logs'),
]
