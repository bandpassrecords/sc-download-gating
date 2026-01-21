# Testing Email Sending in Django

## Quick Test via Django Shell

### 1. Open Django Shell
```bash
python manage.py shell
```

### 2. Test Basic Email Sending

```python
from django.core.mail import send_mail
from django.conf import settings

# Test email
send_mail(
    subject='Test Email from SoundCloud Download Gating By BandPass Records',
    message='This is a test email to verify email configuration is working.',
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=['your-email@example.com'],  # Replace with your email
    fail_silently=False,
)
```

### 3. Test HTML Email (like verification emails)

```python
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

# Render HTML template
html_message = render_to_string('accounts/email_verification.html', {
    'user': {'email': 'test@example.com'},
    'verification_url': 'https://dmh.bandpassrecords.com/accounts/verify-email/test-token/',
    'expires_in': '10 minutes',
})
plain_message = strip_tags(html_message)

# Send email
send_mail(
    subject='Test Verification Email - SoundCloud Download Gating By BandPass Records',
    message=plain_message,
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=['your-email@example.com'],  # Replace with your email
    html_message=html_message,
    fail_silently=False,
)
```

### 4. Check Email Configuration

```python
from django.conf import settings

print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
```

### 5. Test with Console Backend (Development)

If you want to see emails in the console instead of actually sending them:

```python
from django.core.mail import send_mail
from django.conf import settings

# Temporarily use console backend
from django.core.mail import get_connection
from django.core.mail.backends.console import EmailBackend

connection = EmailBackend()
send_mail(
    subject='Test Email',
    message='This will print to console',
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=['test@example.com'],
    connection=connection,
)
```

## Common Issues

### Issue: Email not sending
- Check that `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are set correctly in `.env`
- For Gmail: Make sure you're using an App Password, not your regular password
- Check firewall/network settings if using SMTP

### Issue: Authentication failed
- Verify your email credentials are correct
- For Gmail: Ensure 2-Factor Authentication is enabled and you're using an App Password
- Check that `EMAIL_USE_TLS` is set to `True` for most providers

### Issue: Connection timeout
- Check that `EMAIL_HOST` and `EMAIL_PORT` are correct for your provider
- Verify network connectivity to the SMTP server
- Check if your server's IP is blocked by the email provider

## Email Provider Settings Reference

### Gmail
- EMAIL_HOST: `smtp.gmail.com`
- EMAIL_PORT: `587`
- EMAIL_USE_TLS: `True`
- EMAIL_HOST_USER: `your-email@gmail.com`
- EMAIL_HOST_PASSWORD: `your-16-char-app-password`

### SendGrid
- EMAIL_HOST: `smtp.sendgrid.net`
- EMAIL_PORT: `587`
- EMAIL_USE_TLS: `True`
- EMAIL_HOST_USER: `apikey`
- EMAIL_HOST_PASSWORD: `your-sendgrid-api-key`

### Mailgun
- EMAIL_HOST: `smtp.mailgun.org`
- EMAIL_PORT: `587`
- EMAIL_USE_TLS: `True`
- EMAIL_HOST_USER: `your-mailgun-smtp-username`
- EMAIL_HOST_PASSWORD: `your-mailgun-smtp-password`


