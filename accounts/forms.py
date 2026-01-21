from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from .models import UserProfile


class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form - email only, no username, no first/last name"""
    email = forms.EmailField(required=True, help_text="Required. Enter a valid email address.")
    
    class Meta:
        model = User
        fields = ("email", "password1", "password2")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove username field
        if 'username' in self.fields:
            del self.fields['username']
        # Add CSS classes to form fields (no placeholders)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control form-control-lg'
            if field_name == 'email':
                field.widget.attrs['autocomplete'] = 'email'
                field.help_text = None
            elif field_name == 'password1':
                field.widget.attrs['autocomplete'] = 'new-password'
                # Keep help_text for error display (template will show it only on error)
            elif field_name == 'password2':
                field.widget.attrs['autocomplete'] = 'new-password'
                # Remove the default help text for password2
                field.help_text = None
    
    def clean_email(self):
        """Validate that email doesn't already exist"""
        email = self.cleaned_data.get('email')
        if email:
            if User.objects.filter(email=email).exists():
                raise ValidationError('A user with this email address already exists.')
        return email
    
    def save(self, commit=True):
        # Get email first - it must exist (validated by clean_email)
        email = self.cleaned_data.get("email")
        if not email:
            raise ValueError("Email is required but was not provided")
        
        # Set username to email, but ensure it's unique
        # If username already exists, append a number
        base_username = email.strip()  # Remove any whitespace
        if not base_username:
            raise ValueError("Email cannot be empty")
        
        password = self.cleaned_data.get("password1")
        if not password:
            raise ValueError("Password is required")
        
        # Retry logic to handle race conditions when multiple users sign up simultaneously
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                with transaction.atomic():
                    # Use select_for_update to lock rows and prevent race conditions
                    # Check if username exists with a lock
                    username = base_username
                    counter = 1
                    
                    # Try the base username first
                    if User.objects.select_for_update().filter(username=username).exists():
                        # Generate unique username by appending counter
                        while User.objects.select_for_update().filter(username=username).exists():
                            username = f"{base_username}_{counter}"
                            counter += 1
                            # Safety limit to prevent infinite loops
                            if counter > 10000:
                                raise ValueError(f"Unable to generate unique username after {counter} attempts")
                    
                    # Create user object directly to avoid UserCreationForm's username handling
                    user = User(
                        username=username,
                        email=email,
                        is_active=False  # User must verify email before account is active
                    )
                    
                    # Set password using set_password (from UserCreationForm)
                    user.set_password(password)
                    
                    if commit:
                        user.save()
                    
                    return user
                    
            except IntegrityError as e:
                # If we get an integrity error (duplicate username), retry
                if 'username' in str(e).lower() or 'unique constraint' in str(e).lower():
                    if attempt < max_attempts - 1:
                        # Wait a small random amount before retrying (helps with concurrent requests)
                        import time
                        import random
                        time.sleep(random.uniform(0.01, 0.1))
                        continue
                    else:
                        raise ValueError(f"Unable to create user after {max_attempts} attempts due to username conflicts. Please try again.")
                else:
                    # Different integrity error, don't retry
                    raise
        
        raise ValueError("Failed to create user after multiple attempts")


class DeleteAccountForm(forms.Form):
    """Form for account deletion confirmation"""
    confirm_delete = forms.BooleanField(
        required=True,
        label="I understand this action cannot be undone",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        """Initialize form"""
        super().__init__(*args, **kwargs)
    
    def clean(self):
        return super().clean()


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile"""
    
    class Meta:
        model = UserProfile
        fields = [
            'bio', 'avatar',
            'show_email', 'show_real_name',
            'notify_on_downloads',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Tell us about yourself...'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control-file'}),
            'show_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_real_name': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_on_downloads': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'bio': 'Brief description about yourself and your music production background.',
            'show_email': 'Allow other users to see your email address.',
            'show_real_name': 'Display your real name (first name + surname) instead of the generated fake name. Only works if you have both first name and surname set.',
            'notify_on_downloads': 'Email me when someone downloads a file from one of my gates. If disabled, gate-level email settings will be ignored.',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show show_real_name option if user has first_name and last_name
        if self.instance and self.instance.user:
            user = self.instance.user
            if not (user.first_name and user.last_name):
                # Hide the field if user doesn't have both names
                if 'show_real_name' in self.fields:
                    self.fields['show_real_name'].widget = forms.HiddenInput()
                    # Set to False if they don't have names
                    self.initial['show_real_name'] = False


class UserUpdateForm(forms.ModelForm):
    """Form for updating basic user information - email only, no username"""
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': True, 'style': 'background-color: #7e7e7e;'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        # Make email read-only (cannot be changed)
        # Use readonly instead of disabled so the value is still submitted
        self.fields['email'].widget.attrs['readonly'] = True
        # Set light grey background for better contrast
        self.fields['email'].widget.attrs['style'] = 'background-color: #7e7e7e; cursor: not-allowed;'
        # Remove username field if it exists
        if 'username' in self.fields:
            del self.fields['username']
    
    def save(self, commit=True):
        """Override save to prevent email from being changed"""
        user = super().save(commit=False)
        # Always keep the original email (don't allow changes)
        if self.instance and self.instance.pk:
            user.email = self.instance.email
        if commit:
            user.save()
        return user


class CustomPasswordResetForm(PasswordResetForm):
    """Custom password reset form with Bootstrap styling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })


class CustomSetPasswordForm(SetPasswordForm):
    """Custom set password form with Bootstrap styling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter new password'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
