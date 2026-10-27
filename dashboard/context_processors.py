from items.models import ItemReport, ItemMatch
from claims.models import RecoveryRecord


def system_stats_processor(request):
    """Context processor providing high-level system metrics and admin status."""
    is_admin = False
    if request.user.is_authenticated:
        is_admin = getattr(request.user, 'is_admin_or_staff', False)

    return {
        'can_access_admin_dashboard': is_admin,
    }
