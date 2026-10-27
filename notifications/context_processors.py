from .models import Notification


def unread_notifications_processor(request):
    """Context processor providing unread notifications count and recent alerts to base templates."""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        navbar_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]
        return {
            'unread_notifications_count': unread_count,
            'navbar_notifications': navbar_notifications,
        }
    return {
        'unread_notifications_count': 0,
        'navbar_notifications': [],
    }
