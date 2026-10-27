from django.urls import path
from . import views

app_name = 'items'

urlpatterns = [
    path('report/lost/', views.report_submit_view, {'report_type': 'LOST'}, name='report_lost'),
    path('report/found/', views.report_submit_view, {'report_type': 'FOUND'}, name='report_found'),
    path('report/<str:report_id>/', views.report_detail_view, name='report_detail'),
    path('report/<str:report_id>/edit/', views.report_edit_view, name='report_edit'),
    path('public-listings/', views.approved_public_list_view, name='public_list'),
]
