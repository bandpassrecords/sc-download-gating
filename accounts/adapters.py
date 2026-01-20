"""
Custom adapters for django-allauth to handle social account signups.
"""
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
import random
import time


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for social account signups.
    Sets username to email address and handles uniqueness.
    """
    
    def populate_user(self, request, sociallogin, data):
        """
        Populate user instance with data from social account.
        Override to set username from email.
        """
        # Get the base user from the default adapter
        user = super().populate_user(request, sociallogin, data)
        
        # Get email from social account data
        email = data.get('email') or sociallogin.account.extra_data.get('email')
        
        if email:
            email = email.strip()
            # Set username to email, ensuring it's unique
            # Note: We can't use select_for_update here since user isn't saved yet
            # The actual uniqueness check and retry will happen in save_user()
            base_username = email
            username = base_username
            counter = 1
            
            # Check if username exists (without lock since user isn't saved)
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
                if counter > 10000:
                    raise ValueError(f"Unable to generate unique username after {counter} attempts")
            
            # Set the username
            user.username = username
            
            # Ensure email is set
            if not user.email:
                user.email = email
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Save the user account.
        Override to ensure username is set correctly and handle race conditions.
        """
        # Get the user from the adapter
        user = sociallogin.user
        
        # Ensure username is set (fallback if populate_user didn't set it)
        if not user.username or user.username == '':
            email = user.email or sociallogin.account.extra_data.get('email', '')
            if email:
                email = email.strip()
                base_username = email
                username = base_username
                counter = 1
                
                # Ensure uniqueness
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                    if counter > 10000:
                        raise ValueError("Unable to generate unique username")
                
                user.username = username
        
        # Retry logic to handle race conditions when saving
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                with transaction.atomic():
                    # Double-check username uniqueness before saving
                    if User.objects.select_for_update().filter(username=user.username).exists():
                        # Username was taken, generate a new one
                        email = user.email or sociallogin.account.extra_data.get('email', '')
                        if email:
                            base_username = email.strip()
                            counter = 1
                            while User.objects.select_for_update().filter(username=user.username).exists():
                                user.username = f"{base_username}_{counter}"
                                counter += 1
                                if counter > 10000:
                                    raise ValueError("Unable to generate unique username")
                    
                    # Call parent to save
                    return super().save_user(request, sociallogin, form)
                    
            except IntegrityError as e:
                # If we get an integrity error (duplicate username), retry
                if 'username' in str(e).lower() or 'unique constraint' in str(e).lower():
                    if attempt < max_attempts - 1:
                        # Generate new username and retry
                        email = user.email or sociallogin.account.extra_data.get('email', '')
                        if email:
                            base_username = email.strip()
                            counter = 1
                            while User.objects.filter(username=user.username).exists():
                                user.username = f"{base_username}_{counter}"
                                counter += 1
                                if counter > 10000:
                                    raise ValueError("Unable to generate unique username")
                        time.sleep(random.uniform(0.01, 0.1))
                        continue
                    else:
                        raise ValueError(f"Unable to create user after {max_attempts} attempts due to username conflicts")
                else:
                    # Different integrity error, don't retry
                    raise
        
        # Fallback to parent if retries exhausted
        return super().save_user(request, sociallogin, form)


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter for regular (non-social) account signups.
    Ensures username is set from email if not already set.
    """
    
    def save_user(self, request, user, form, commit=True):
        """
        Save the user account.
        Ensure username is set from email if it's empty.
        """
        # If username is empty or not set, set it from email
        if not user.username or user.username == '':
            email = user.email or form.cleaned_data.get('email', '')
            if email:
                email = email.strip()
                base_username = email
                username = base_username
                counter = 1
                
                # Ensure uniqueness
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                    if counter > 10000:
                        raise ValueError("Unable to generate unique username")
                
                user.username = username
        
        # Call parent to save
        return super().save_user(request, user, form, commit=commit)

