from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from items.models import ItemReport, AuditLog
from claims.models import OwnershipClaim
from notifications.models import Notification
from .forms import StudentRegistrationForm, StudentLoginForm, ProfileUpdateForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to the Campus Lost & Found System, {user.first_name or user.username}!")
            
            # Welcome notification
            Notification.objects.create(
                recipient=user,
                title="Welcome to Campus Recovery Portal",
                message="Your account is active. You can report lost or found belongings and track verification in real time.",
                link="/accounts/dashboard/",
                notification_type='SYSTEM'
            )

            AuditLog.objects.create(
                actor=user,
                action_type='USER_REGISTERED',
                target_model='User',
                target_id=str(user.id),
                details=f"User {user.username} registered with email {user.email}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return redirect('accounts:dashboard')
        else:
            messages.error(request, "Please resolve the errors highlighted below.")
    else:
        form = StudentRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = StudentLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            if getattr(user, 'is_admin_or_staff', False):
                return redirect('dashboard:overview')
            return redirect('accounts:dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = StudentLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect('public_home')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def student_dashboard_view(request):
    user = request.user
    user_reports = ItemReport.objects.filter(reporter=user).order_by('-created_at')
    user_claims = OwnershipClaim.objects.filter(claimant=user).order_by('-created_at')
    recent_notifications = Notification.objects.filter(recipient=user).order_by('-created_at')[:8]

    # Metrics
    total_reports = user_reports.count()
    pending_count = user_reports.filter(approval_status='PENDING').count()
    approved_count = user_reports.filter(approval_status='APPROVED').count()
    needs_info_count = user_reports.filter(approval_status='NEEDS_INFORMATION').count()
    claims_count = user_claims.count()

    context = {
        'user_reports': user_reports,
        'user_claims': user_claims,
        'recent_notifications': recent_notifications,
        'total_reports': total_reports,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'needs_info_count': needs_info_count,
        'claims_count': claims_count,
    }
    return render(request, 'accounts/dashboard.html', context)
