from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.db import transaction, OperationalError, models
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone
import time
from allauth.account.views import LoginView as AllauthLoginView
from .forms import CustomUserCreationForm, UserProfileForm, UserUpdateForm, DeleteAccountForm, CustomPasswordResetForm
from .models import UserProfile, EmailVerification
from gates.models import GatedTrack


def get_deleted_user():
    """Get or create a system user for deleted accounts"""
    username = 'deleted_account'
    email = 'deleted@system.local'
    
    deleted_user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'first_name': 'Deleted',
            'last_name': 'Account',
            'is_active': False,  # Cannot log in
            'is_staff': False,
            'is_superuser': False,
        }
    )
    
    # Ensure user is inactive
    if not deleted_user.is_active:
        deleted_user.is_active = False
        deleted_user.save()
    
    # Create or get profile for deleted user
    profile, _ = UserProfile.objects.get_or_create(
        user=deleted_user,
        defaults={
            'generated_display_name': 'Deleted Account',
            'show_email': False,
            'show_real_name': False,
        }
    )
    
    # Ensure display name is set
    if not profile.generated_display_name:
        profile.generated_display_name = 'Deleted Account'
        profile.save()
    
    return deleted_user


class CustomLoginView(AllauthLoginView):
    """Custom login view using allauth but with our template"""
    template_name = 'accounts/login.html'
    
    def form_invalid(self, form):
        """Handle invalid form submission - check if account is unverified"""
        response = super().form_invalid(form)
        
        # Check if login failed due to unverified email
        login_value = form.cleaned_data.get('login', '')
        if login_value:
            try:
                # Try to find user by email or username
                user = User.objects.filter(
                    models.Q(email=login_value) | models.Q(username=login_value)
                ).first()
                
                if user and not user.is_active:
                    # Check if there's an unverified email verification
                    try:
                        verification = user.email_verification
                        if not verification.verified:
                            # Store email in session for resend functionality
                            self.request.session['unverified_email'] = user.email
                            self.request.session.modified = True
                    except EmailVerification.DoesNotExist:
                        pass
            except Exception:
                pass
        
        return response


class CustomPasswordResetView(auth_views.PasswordResetView):
    """Custom password reset view that ensures correct domain is used"""
    template_name = 'accounts/password_reset.html'
    email_template_name = 'registration/password_reset_email.txt'  # Plain text version
    html_email_template_name = 'registration/password_reset_email.html'  # HTML version
    subject_template_name = 'registration/password_reset_email_subject.txt'
    form_class = CustomPasswordResetForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ensure domain is set correctly from the request
        current_site = get_current_site(self.request)
        context['domain'] = current_site.domain
        context['site_name'] = current_site.name or getattr(settings, 'APP_DISPLAY_NAME', 'sc_download_gating')
        return context
    
    def form_valid(self, form):
        # Override to ensure domain is correct in email context and HTML email is sent
        # Build the email options with our custom settings
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
            'html_email_template_name': self.html_email_template_name,  # This enables HTML emails
            'extra_email_context': {
                'domain': get_current_site(self.request).domain,
                'site_name': get_current_site(self.request).name or getattr(settings, 'APP_DISPLAY_NAME', 'sc_download_gating'),
            }
        }
        # Call form.save() with our options - this sends the email
        form.save(**opts)
        # Return redirect to success page (don't call super() to avoid duplicate email)
        return redirect(self.get_success_url())


def signup(request):
    """Signup choice page - choose between Google or email registration"""
    return render(request, 'accounts/signup.html')


def signup_email(request):
    """Email-only signup view with email verification"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Retry logic for SQLite database locks
            max_retries = 3
            retry_delay = 0.1  # Start with 100ms
            
            user = None
            token = None
            email = None
            
            for attempt in range(max_retries):
                try:
                    with transaction.atomic():
                        user = form.save()
                        email = form.cleaned_data.get('email')
                        
                        # Generate verification token
                        token = EmailVerification.generate_token()
                        EmailVerification.objects.create(
                            user=user,
                            token=token
                        )
                    break  # Success, exit retry loop
                except OperationalError as e:
                    if 'database is locked' in str(e).lower() and attempt < max_retries - 1:
                        # Wait before retrying with exponential backoff
                        time.sleep(retry_delay * (2 ** attempt))
                        continue
                    else:
                        # Re-raise if it's not a lock error or we've exhausted retries
                        messages.error(request, 'Database is temporarily busy. Please try again in a moment.')
                        return render(request, 'accounts/signup_email.html', {'form': form})
            
            if not user or not token:
                messages.error(request, 'Failed to create account. Please try again.')
                return render(request, 'accounts/signup_email.html', {'form': form})
            
            # Send verification email (outside retry loop, only if user creation succeeded)
            verification_url = request.build_absolute_uri(
                f'/accounts/verify-email/{token}/'
            )
            
            # Render email template
            html_message = render_to_string('accounts/email_verification.html', {
                'user': user,
                'verification_url': verification_url,
                'expires_in': '10 minutes',
            })
            plain_message = strip_tags(html_message)
            
            try:
                send_mail(
                    subject='Verify your email address',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    html_message=html_message,
                    fail_silently=False,
                )
                messages.success(
                    request,
                    f'Account created! Please check your email ({email}) and click the verification link to activate your account. The link expires in 10 minutes.'
                )
                return redirect('accounts:verification_sent')
            except Exception as e:
                # If email fails, delete the user and show error
                user.delete()
                messages.error(
                    request,
                    f'Failed to send verification email. Please try again. Error: {str(e)}'
                )
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/signup_email.html', {'form': form})


def verify_email(request, token):
    """Verify email address using token"""
    try:
        verification = EmailVerification.objects.get(token=token)
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('accounts:signup')
    
    if verification.verified:
        messages.info(request, 'Your email has already been verified. You can log in.')
        return redirect('accounts:login')
    
    if verification.is_expired():
        # Delete expired verification and user
        user = verification.user
        verification.delete()
        user.delete()
        messages.error(
            request,
            'Verification link has expired. Please sign up again to receive a new verification email.'
        )
        return redirect('accounts:signup')
    
    # Verify the email
    verification.verify()
    
    messages.success(
        request,
        'Email verified successfully! Your account has been activated. You can now log in.'
    )
    return redirect('accounts:login')


def verification_sent(request):
    """Page shown after verification email is sent"""
    return render(request, 'accounts/verification_sent.html')


@require_http_methods(["POST"])
def resend_verification_email(request):
    """Resend verification email for unverified accounts"""
    email = request.POST.get('email') or request.session.get('unverified_email')
    
    if not email:
        return JsonResponse({
            'success': False,
            'message': 'Email address is required.'
        })
    
    try:
        user = User.objects.get(email=email)
        
        # Check if user is already verified/active
        if user.is_active:
            # Clear session
            if 'unverified_email' in request.session:
                del request.session['unverified_email']
                request.session.modified = True
            return JsonResponse({
                'success': False,
                'message': 'This account is already verified and active.'
            })
        
        # Get or create email verification
        verification, created = EmailVerification.objects.get_or_create(
            user=user,
            defaults={'token': EmailVerification.generate_token()}
        )
        
        # If verification exists but is expired or already verified, create a new one
        if not created:
            if verification.verified:
                return JsonResponse({
                    'success': False,
                    'message': 'This account is already verified.'
                })
            # Generate new token if expired
            if verification.is_expired():
                verification.token = EmailVerification.generate_token()
                verification.created_at = timezone.now()
                verification.save()
        
        # Send verification email
        verification_url = request.build_absolute_uri(
            f'/accounts/verify-email/{verification.token}/'
        )
        
        html_message = render_to_string('accounts/email_verification.html', {
            'user': user,
            'verification_url': verification_url,
            'expires_in': '10 minutes',
        })
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject='Verify your email address',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
            
            # Clear session
            if 'unverified_email' in request.session:
                del request.session['unverified_email']
                request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'message': f'Verification email has been sent to {email}. Please check your inbox and click the verification link. The link expires in 10 minutes.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Failed to send verification email. Please try again later. Error: {str(e)}'
            })
            
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'No account found with this email address.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })


@login_required
def profile(request):
    """User profile view - shows user's gated downloads"""
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    tracks_qs = GatedTrack.objects.filter(owner=request.user).order_by("-created_at")

    total_gates = tracks_qs.count()
    total_downloads = (
        tracks_qs.aggregate(total=models.Sum("download_count")).get("total") or 0
    )

    context = {
        "profile": user_profile,
        "profile_user": request.user,
        "tracks": tracks_qs[:200],
        "total_gates": total_gates,
        "total_downloads": total_downloads,
        "is_own_profile": True,
    }

    return render(request, "accounts/profile.html", context)


@login_required
def edit_profile(request):
    """Edit user profile view"""
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        
        # Handle avatar removal
        if request.POST.get('avatar-clear') == '1':
            if user_profile.avatar:
                user_profile.avatar.delete(save=False)
                user_profile.avatar = None
        
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileForm(instance=user_profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    
    return render(request, 'accounts/edit_profile.html', context)


@login_required
def dashboard(request):
    """User dashboard with overview"""
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    tracks_qs = GatedTrack.objects.filter(owner=request.user).order_by("-created_at")
    recent_tracks = tracks_qs[:5]
    popular_tracks = tracks_qs.order_by("-download_count", "-created_at")[:5]

    total_gates = tracks_qs.count()
    total_downloads = (
        tracks_qs.aggregate(total=models.Sum("download_count")).get("total") or 0
    )

    context = {
        "profile": user_profile,
        "recent_tracks": recent_tracks,
        "popular_tracks": popular_tracks,
        "total_gates": total_gates,
        "total_downloads": total_downloads,
    }

    return render(request, "accounts/dashboard.html", context)


@login_required
def delete_account(request):
    """Delete user account view"""
    if request.method == 'POST':
        form = DeleteAccountForm(request.POST)
        if form.is_valid() and form.cleaned_data['confirm_delete']:
            user = request.user
            
            with transaction.atomic():
                messages.success(request, 'Your account has been deleted.')
                
                # Logout before deleting user
                logout(request)
                
                # Delete user (this will cascade delete UserProfile and owned gates)
                user.delete()
                
                return redirect('core:home')
        else:
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            else:
                messages.error(request, 'Please confirm that you understand this action cannot be undone.')
    else:
        form = DeleteAccountForm()
    
    context = {'form': form}
    return render(request, 'accounts/delete_account.html', context)
