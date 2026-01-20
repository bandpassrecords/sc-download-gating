"""
Base settings for sc_download_gate project.

These settings are shared by both development and production environments.
"""

from pathlib import Path
import os
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# ============================================================================
# SECURITY SETTINGS
# ============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
# Generate a new secret key: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
SECRET_KEY = config('SECRET_KEY', default='django-insecure-t^6zgheq3rvc&k82xos5+&a!#cb5vo_r^o70x!y%f$upx5jo4&')

# Allowed hosts - set in environment variable as comma-separated list
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())

# App branding
APP_NAME = config('APP_NAME', default='sc_download_gating')
APP_DISPLAY_NAME = config('APP_DISPLAY_NAME', default=APP_NAME)


# ============================================================================
# APPLICATION DEFINITION
# ============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Required for allauth
    
    # Third-party apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    
    # Local apps
    'core',
    'accounts',
    'gates',
    'macros',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files efficiently
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Required for allauth
]

# Authentication backends
AUTHENTICATION_BACKENDS = [
    # Django's default authentication backend
    'django.contrib.auth.backends.ModelBackend',
    # Allauth authentication backend
    'allauth.account.auth_backends.AuthenticationBackend',
]

ROOT_URLCONF = 'sc_download_gate.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.app_brand',
            ],
        },
    },
]

WSGI_APPLICATION = 'sc_download_gate.wsgi.application'


# ============================================================================
# DATABASE
# ============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 30,  # SQLite timeout in seconds (increased for production)
            'check_same_thread': False,  # Allow multiple threads
        },
        # IMPORTANT: SQLite doesn't support connection pooling well
        # Set to 0 to close connections immediately (prevents locks)
        'CONN_MAX_AGE': 0,  # Close connections immediately for SQLite
    }
}


# ============================================================================
# PASSWORD VALIDATION
# ============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ============================================================================
# INTERNATIONALIZATION
# ============================================================================

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# ============================================================================
# STATIC FILES
# ============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Only include static directory if it exists (prevents warnings)
STATICFILES_DIRS = []
static_dir = BASE_DIR / 'static'
if static_dir.exists():
    STATICFILES_DIRS.append(static_dir)

# WhiteNoise configuration for efficient static file serving
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================================================
# AUTHENTICATION & LOGIN
# ============================================================================

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'


# ============================================================================
# DJANGO ALLAUTH SETTINGS
# ============================================================================

SITE_ID = 1  # Required for allauth

# Allauth Account Settings
ACCOUNT_AUTHENTICATION_METHOD = 'email'  # Use email only for authentication
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # 'mandatory', 'optional', or 'none'
ACCOUNT_USERNAME_REQUIRED = False  # Username not required
ACCOUNT_USER_MODEL_USERNAME_FIELD = None  # Don't use username field
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE = False
ACCOUNT_SESSION_REMEMBER = True  # Remember user login
ACCOUNT_USER_MODEL_EMAIL_FIELD = 'email'  # Use email as primary identifier
ACCOUNT_ADAPTER = 'accounts.adapters.CustomAccountAdapter'  # Custom adapter for regular signups
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.CustomSocialAccountAdapter'  # Custom adapter for social signups

# Social Account Settings
SOCIALACCOUNT_AUTO_SIGNUP = True  # Automatically create account on social login
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'optional'
SOCIALACCOUNT_QUERY_EMAIL = True  # Request email from provider

# Google OAuth Settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'APP': {
            'client_id': config('GOOGLE_CLIENT_ID', default=''),
            'secret': config('GOOGLE_CLIENT_SECRET', default=''),
            'key': ''
        }
    }
}

#
# ============================================================================
# SOUNDCLOUD OAUTH (Gated Downloads)
# ============================================================================
#
SOUNDCLOUD_CLIENT_ID = config('SOUNDCLOUD_CLIENT_ID', default='')
SOUNDCLOUD_CLIENT_SECRET = config('SOUNDCLOUD_CLIENT_SECRET', default='')
# Optional, defaults to "*" (SoundCloud docs do not consistently document scopes)
SOUNDCLOUD_OAUTH_SCOPE = config('SOUNDCLOUD_OAUTH_SCOPE', default='*')
# Optional override. If set, this exact URL is used as redirect_uri for SoundCloud OAuth.
# Example: https://download.bandpassrecords.com/authorize
SOUNDCLOUD_REDIRECT_URI = config('SOUNDCLOUD_REDIRECT_URI', default='')


# ============================================================================
# FILE UPLOAD SETTINGS
# ============================================================================

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB


# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================

# Email backend - defaults to console, override in production.py
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')

# SMTP Configuration (set via environment variables)
EMAIL_HOST = config('EMAIL_HOST', default='smtp.protonmail.ch')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
# Email address (can be overridden with display name format: "Display Name <email@example.com>")
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=f'{APP_DISPLAY_NAME} <dmh@bandpassrecords.com>')
SERVER_EMAIL = config('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)


# ============================================================================
# SESSION SECURITY (Common)
# ============================================================================

SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
SESSION_COOKIE_AGE = 86400  # 24 hours


# ============================================================================
# CSRF SECURITY (Common)
# ============================================================================

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())


# ============================================================================
# SECURITY HEADERS (Common)
# ============================================================================

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking

# Password Reset Token
PASSWORD_RESET_TIMEOUT = 86400  # 24 hours (in seconds)


