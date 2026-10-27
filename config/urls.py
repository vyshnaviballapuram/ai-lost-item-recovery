from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # Technical Django Admin for Technical Superusers
    path('technical-admin/', admin.site.urls),

    # Core System Apps
    path('accounts/', include('accounts.urls')),
    path('items/', include('items.urls')),
    path('claims/', include('claims.urls')),
    path('notifications/', include('notifications.urls')),
    path('admin-dashboard/', include('dashboard.urls')),

    # Public Informational Pages
    path('', views.public_home_view, name='public_home'),
    path('about/', views.public_about_view, name='public_about'),
    path('privacy/', views.public_privacy_view, name='public_privacy'),
    path('health/', views.health_check_view, name='health_check'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
