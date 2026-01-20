# Email Configuration Guide

This guide explains how to set up email for password reset functionality in your Django application.

## Development Setup (Console Backend)

For development, the easiest option is to use the console backend, which prints emails to your terminal instead of actually sending them.

**Current Configuration:**
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

This is already configured in `settings.py`. When you request a password reset, you'll see the email content printed in your terminal/console.

## Production Setup (SMTP Backend)

For production, you need to configure an SMTP email backend. Here are options for different email providers:

### Option 1: Gmail

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate an App Password:**
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Enter "Django App" and click Generate
   - Copy the 16-character password

3. **Update settings.py:**
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-16-char-app-password'
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'
SERVER_EMAIL = 'your-email@gmail.com'
```

### Option 2: SendGrid (Recommended for Production)

1. **Sign up** at https://sendgrid.com (free tier: 100 emails/day)
2. **Create an API Key:**
   - Go to Settings > API Keys
   - Create a new API key with "Mail Send" permissions
   - Copy the API key

3. **Update settings.py:**
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = 'your-sendgrid-api-key'
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
SERVER_EMAIL = 'noreply@yourdomain.com'
```

### Option 3: Mailgun

1. **Sign up** at https://www.mailgun.com (free tier: 5,000 emails/month)
2. **Get SMTP credentials** from your Mailgun dashboard
3. **Update settings.py:**
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.mailgun.org'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-mailgun-smtp-username'
EMAIL_HOST_PASSWORD = 'your-mailgun-smtp-password'
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
SERVER_EMAIL = 'noreply@yourdomain.com'
```

### Option 4: Outlook/Hotmail

1. **Enable 2-Factor Authentication** on your Microsoft account
2. **Generate an App Password:**
   - Go to https://account.microsoft.com/security
   - Under "App passwords", create a new one
   - Copy the password

3. **Update settings.py:**
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp-mail.outlook.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@outlook.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'your-email@outlook.com'
SERVER_EMAIL = 'your-email@outlook.com'
```

## Using Environment Variables (Recommended)

For security, store sensitive email credentials in environment variables:

1. **Install python-decouple:**
```bash
pip install python-decouple
```

2. **Create a `.env` file** in your project root:
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

3. **Update settings.py:**
```python
from decouple import config

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@example.com')
SERVER_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@example.com')
```

**Important:** Add `.env` to your `.gitignore` file to keep credentials secure!

## Testing Email Configuration

Test your email setup with Django shell:

```python
python manage.py shell
```

```python
from django.core.mail import send_mail

send_mail(
    'Test Email',
    'This is a test email from Django.',
    'from@example.com',
    ['to@example.com'],
    fail_silently=False,
)
```

## Password Reset Email Templates

Django uses default templates for password reset emails. To customize them, create:

1. `templates/registration/password_reset_email.html` - Email body
2. `templates/registration/password_reset_email_subject.txt` - Email subject

Example `password_reset_email.html`:
```html
{% load i18n %}{% autoescape off %}
Hello,

You're receiving this email because you requested a password reset for your account on {{ site_name }}.

Please go to the following page and choose a new password:
{% block reset_link %}
{{ protocol }}://{{ domain }}{% url 'accounts:password_reset_confirm' uidb64=uid token=token %}
{% endblock %}

If you didn't request this, please ignore this email.

Thanks,
The {{ site_name }} Team
{% endautoescape %}
```

Example `password_reset_email_subject.txt`:
```
Password reset for {{ site_name }}
```

## Troubleshooting

### Gmail: "Less secure app access" error
- Gmail no longer supports "less secure apps"
- You MUST use an App Password (see Option 1 above)

### Emails going to spam
- Use a proper email service (SendGrid, Mailgun) instead of personal Gmail
- Set up SPF and DKIM records for your domain
- Use a proper "From" address (not a free email service)

### Connection timeout
- Check your firewall settings
- Verify EMAIL_PORT is correct (587 for TLS, 465 for SSL)
- Some networks block SMTP ports


