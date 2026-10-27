from django.urls import path
from . import views

app_name = 'claims'

urlpatterns = [
    path('submit/<str:report_id>/', views.submit_claim_view, name='submit_claim'),
    path('detail/<str:claim_id>/', views.claim_detail_view, name='claim_detail'),
    path('my-claims/', views.my_claims_list_view, name='my_claims'),
]
