from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import Notification


@login_required
def notification_list_view(request):
    """View all in-app notifications for the authenticated user."""
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications,
    })


@login_required
def mark_read_view(request, notif_id):
    """Mark a notification as read and redirect to its associated target link if present."""
    notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})

    if notif.link:
        return redirect(notif.link)
    return redirect('notifications:list')


@login_required
def mark_all_read_view(request):
    """Mark all user notifications as read."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('notifications:list')
