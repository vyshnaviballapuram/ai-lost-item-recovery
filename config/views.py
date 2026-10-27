from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from items.models import ItemReport, ItemMatch, Category
from claims.models import RecoveryRecord


def public_home_view(request):
    """
    Public Landing Page.
    CRITICAL: Never shows pending, rejected, private photos or confidential details.
    Displays only approved public items, live campus statistics, and system workflow.
    """
    # Live database statistics
    total_approved = ItemReport.objects.filter(approval_status='APPROVED', is_publicly_visible=True).count()
    total_recovered = RecoveryRecord.objects.count()
    total_matches_evaluated = ItemMatch.objects.count()
    categories = Category.objects.all()

    # Approved public items preview (latest 6)
    recent_approved = ItemReport.objects.filter(
        approval_status='APPROVED',
        is_publicly_visible=True
    ).select_related('category').prefetch_related('images').order_by('-date_occurred')[:6]

    context = {
        'total_approved': total_approved,
        'total_recovered': total_recovered,
        'total_matches_evaluated': total_matches_evaluated,
        'categories': categories,
        'recent_approved': recent_approved,
    }
    return render(request, 'public/home.html', context)


def public_about_view(request):
    """About the AI-Based Campus Lost-Item Recovery System."""
    return render(request, 'public/about.html')


def public_privacy_view(request):
    """Data Privacy & Confidential Markings Policy."""
    return render(request, 'public/privacy.html')


def health_check_view(request):
    """Production health-check endpoint for Render and monitoring."""
    db_status = "connected"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    status_code = 200 if db_status == "connected" else 503
    return JsonResponse({
        'status': 'healthy' if status_code == 200 else 'degraded',
        'database': db_status,
        'timestamp': timezone.now().isoformat(),
        'service': 'Campus Lost-Item Recovery System',
    }, status=status_code)
