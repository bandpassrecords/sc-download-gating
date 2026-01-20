# Environment Variables Setup Instructions

This document explains how to set up your `.env` file with all required environment variables.

## Quick Start

1. **Copy the template:**
   ```bash
   cp ENV_TEMPLATE.txt .env
   ```

2. **Edit the `.env` file** and fill in your actual values (see details below)

3. **Important:** The `.env` file is already in `.gitignore` - never commit it to version control!

## Required Environment Variables

### 1. Django Core Settings

#### `DEBUG`
- **Development:** `DEBUG=True`
- **Production:** `DEBUG=False` (MUST be False in production!)
- **Purpose:** Controls debug mode and error pages

#### `SECRET_KEY`
- **How to generate:**
  ```bash
  python manage.py shell
  ```
  Then run:
  ```python
  from django.core.management.utils import get_random_secret_key
  print(get_random_secret_key())
  ```
- **Purpose:** Used for cryptographic signing - MUST be unique and secret
- **⚠️ CRITICAL:** Never use the default value in production!

#### `ALLOWED_HOSTS`
- **Development:** `127.0.0.1,localhost`
- **Production:** `dmh.bandpassrecords.com`
- **Format:** Comma-separated list (no spaces)
- **Purpose:** Security setting that prevents HTTP Host header attacks

### 2. Email Configuration

#### `EMAIL_BACKEND`
- **Development:** `django.core.mail.backends.console.EmailBackend` (prints to console)
- **Production:** `django.core.mail.backends.smtp.EmailBackend` (sends real emails)

#### `EMAIL_HOST`
- **Gmail:** `smtp.gmail.com`
- **Outlook:** `smtp-mail.outlook.com`
- **SendGrid:** `smtp.sendgrid.net`
- **Mailgun:** `smtp.mailgun.org`

#### `EMAIL_PORT`
- **TLS:** `587` (most common)
- **SSL:** `465`

#### `EMAIL_USE_TLS` / `EMAIL_USE_SSL`
- **TLS:** `EMAIL_USE_TLS=True`, `EMAIL_USE_SSL=False`
- **SSL:** `EMAIL_USE_TLS=False`, `EMAIL_USE_SSL=True`

#### `EMAIL_HOST_USER`
- Your email address (e.g., `your-email@gmail.com`)

#### `EMAIL_HOST_PASSWORD`
- **For Gmail:** Use an App Password (not your regular password)
  - Generate at: https://myaccount.google.com/apppasswords
  - Select "Mail" and "Other (Custom name)"
  - Enter "Django App" and generate
  - Copy the 16-character password

#### `DEFAULT_FROM_EMAIL` / `SERVER_EMAIL`
- Email address that appears as sender
- Example: `info@bandpassrecords.com`

### 3. Google OAuth Configuration

#### `GOOGLE_CLIENT_ID`
- Get from: https://console.cloud.google.com/
- Format: `xxxxx.apps.googleusercontent.com`
- See `GOOGLE_AUTH_SETUP.md` for detailed instructions

#### `GOOGLE_CLIENT_SECRET`
- Get from: https://console.cloud.google.com/
- Keep this secret!

### 4. SoundCloud OAuth Configuration (Gated Downloads)

#### `SOUNDCLOUD_CLIENT_ID`
- Get from your SoundCloud developer app settings.

#### `SOUNDCLOUD_CLIENT_SECRET`
- Get from your SoundCloud developer app settings.
- Keep this secret!

#### `SOUNDCLOUD_OAUTH_SCOPE`
- Optional. Defaults to `*`.
- SoundCloud’s OAuth docs don’t consistently document named scopes for read-only endpoints like `/me` and `/me/likes/tracks`, so `*` is used by default.

#### Redirect URL to register in SoundCloud
- In your SoundCloud app settings, register this callback URL:
- `https://YOUR_DOMAIN/g/soundcloud/callback/`
- For local dev it will usually be:
- `http://127.0.0.1:8000/g/soundcloud/callback/`

### 4. Security Settings (Production with HTTPS)

#### `SECURE_SSL_REDIRECT`
- **Development:** `False`
- **Production with SSL:** `True`
- **Purpose:** Redirects all HTTP traffic to HTTPS

#### `SESSION_COOKIE_SECURE`
- **Development:** `False`
- **Production with HTTPS:** `True`
- **Purpose:** Only sends session cookies over HTTPS

#### `CSRF_COOKIE_SECURE`
- **Development:** `False`
- **Production with HTTPS:** `True`
- **Purpose:** Only sends CSRF cookies over HTTPS

#### `CSRF_TRUSTED_ORIGINS`
- **Format:** Comma-separated list of URLs
- **Example:** `https://dmh.bandpassrecords.com`
- **Purpose:** Allows CSRF requests from these origins

### 5. Logging Configuration

#### `DJANGO_LOG_LEVEL`
- Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Development:** `DEBUG` or `INFO`
- **Production:** `INFO` or `WARNING`

## Example .env Files

### Development (.env)
```env
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
ALLOWED_HOSTS=127.0.0.1,localhost
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
GOOGLE_CLIENT_ID=your-dev-client-id
GOOGLE_CLIENT_SECRET=your-dev-secret
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
DJANGO_LOG_LEVEL=DEBUG
```

### Production (.env)
```env
DEBUG=False
SECRET_KEY=your-generated-production-secret-key-here
ALLOWED_HOSTS=dmh.bandpassrecords.com
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=info@bandpassrecords.com
SERVER_EMAIL=info@bandpassrecords.com
GOOGLE_CLIENT_ID=your-production-client-id
GOOGLE_CLIENT_SECRET=your-production-secret
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CSRF_TRUSTED_ORIGINS=https://dmh.bandpassrecords.com
DJANGO_LOG_LEVEL=INFO
```

## Verification

After setting up your `.env` file, verify it's working:

```bash
python manage.py check --deploy
```

This will check for common production issues and security warnings.

## Security Best Practices

1. ✅ **Never commit `.env` to version control** (already in `.gitignore`)
2. ✅ **Use different `SECRET_KEY` for each environment**
3. ✅ **Use App Passwords for Gmail** (not regular passwords)
4. ✅ **Rotate credentials regularly**
5. ✅ **Use environment variables on hosting platforms** (Heroku, Railway, etc.)
6. ✅ **Keep `.env` file permissions restricted** (chmod 600 on Linux/Mac)

## Troubleshooting

### Variables not loading?
- Make sure `.env` file is in the project root (same directory as `manage.py`)
- Check for typos in variable names
- Restart your Django server after changing `.env`

### Email not working?
- Verify `EMAIL_BACKEND` is set correctly
- Check `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`
- For Gmail, make sure you're using an App Password
- Test with console backend first: `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`

### Google OAuth not working?
- Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correct
- Check redirect URIs in Google Cloud Console
- Make sure Site domain is set correctly in Django Admin

## Need Help?

- Django Settings: https://docs.djangoproject.com/en/4.2/ref/settings/
- python-decouple: https://github.com/henriquebastos/python-decouple
- Email Setup: See `EMAIL_SETUP.md`
- Google Auth Setup: See `GOOGLE_AUTH_SETUP.md`

