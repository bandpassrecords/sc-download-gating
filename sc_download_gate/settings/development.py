"""
Development settings for sc_download_gate project.

These settings are used for local development with DEBUG=True.
"""

from .base import *

# ============================================================================
# DEBUG SETTINGS
# ============================================================================

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Development-specific allowed hosts
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0']


SOUNDCLOUD_CLIENT_ID='Lxh5TGHngyLExatHJu3b4dEbC6EohrSg'
SOUNDCLOUD_CLIENT_SECRET='58hmUzSS6B95txAVqV5Jeqkcz1KTU0u2'
SOUNDCLOUD_REDIRECT_URI='download.bandpassrecords.com/authorize'
# EMAIL_HOST_USER=cms@bandpassrecords.com
# Optional. SoundCloud docs do not consistently document scopes; "*" works as a default.
SOUNDCLOUD_OAUTH_SCOPE='*'

# ============================================================================
# DEVELOPMENT-SPECIFIC SETTINGS
# ============================================================================

# Email backend - use console for development (emails printed to terminal)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Session Security (relaxed for development)
SESSION_COOKIE_SECURE = False  # Allow HTTP cookies
CSRF_COOKIE_SECURE = False  # Allow HTTP cookies

# HTTPS Settings (disabled for development)
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0  # Disable HSTS in development

# Security Headers (relaxed for development)
SECURE_PROXY_SSL_HEADER = None


# ============================================================================
# DEVELOPMENT TOOLBAR (Optional)
# ============================================================================

# Uncomment to enable Django Debug Toolbar
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
# INTERNAL_IPS = ['127.0.0.1']


# ============================================================================
# LOGGING (Development - More Verbose)
# ============================================================================

# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'verbose': {
#             'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
#             'style': '{',
#         },
#         'simple': {
#             'format': '{levelname} {message}',
#             'style': '{',
#         },
#     },
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#             'formatter': 'verbose',
#         },
#         'file': {
#             'class': 'logging.handlers.RotatingFileHandler',
#             'filename': BASE_DIR / 'logs' / 'django.log',
#             'maxBytes': 1024 * 1024 * 10,  # 10 MB
#             'backupCount': 5,
#             'formatter': 'verbose',
#         },
#     },
#     'root': {
#         'handlers': ['console', 'file'],
#         'level': 'DEBUG',  # More verbose in development
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['console', 'file'],
#             'level': 'DEBUG',
#             'propagate': False,
#         },
#         'django.request': {
#             'handlers': ['console', 'file'],
#             'level': 'DEBUG',
#             'propagate': False,
#         },
#         'django.security': {
#             'handlers': ['console', 'file'],
#             'level': 'DEBUG',
#             'propagate': False,
#         },
#     },
# }

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)


