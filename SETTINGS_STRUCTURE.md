# Settings Structure Guide

This project uses a modular settings structure to separate development and production configurations.

## Settings Structure

```
sc_download_gate/
├── settings/
│   ├── __init__.py          # Package initialization
│   ├── base.py              # Common settings shared by all environments
│   ├── development.py       # Development settings (DEBUG=True)
│   └── production.py        # Production settings (DEBUG=False)
└── settings.py.old          # Backup of original settings.py
```

## Settings Files

### `base.py`
Contains all common settings shared by both development and production:
- Application definition (INSTALLED_APPS, MIDDLEWARE)
- Database configuration
- Static files configuration
- Authentication settings
- Allauth configuration
- Common security settings
- Email configuration (base settings)

### `development.py`
Extends `base.py` with development-specific settings:
- `DEBUG = True`
- Console email backend
- Relaxed security (HTTP cookies allowed)
- Verbose logging (DEBUG level)
- Development allowed hosts

### `production.py`
Extends `base.py` with production-specific settings:
- `DEBUG = False` (from environment variable)
- SMTP email backend
- Strict security (HTTPS cookies required)
- Production logging (INFO level, email notifications)
- Production allowed hosts
- SSL/HTTPS security settings

## Usage

### Development (Default)

When running locally, Django automatically uses development settings:

```bash
python manage.py runserver
# Uses: sc_download_gate.settings.development
```

Or explicitly:
```bash
DJANGO_SETTINGS_MODULE=sc_download_gate.settings.development python manage.py runserver
```

### Production

For production, set the environment variable:

**Option 1: Environment Variable**
```bash
export DJANGO_SETTINGS_MODULE=sc_download_gate.settings.production
python manage.py runserver
```

**Option 2: In systemd service file:**
```ini
[Service]
Environment="DJANGO_SETTINGS_MODULE=sc_download_gate.settings.production"
```

**Option 3: In Gunicorn command:**
```bash
gunicorn --env DJANGO_SETTINGS_MODULE=sc_download_gate.settings.production sc_download_gate.wsgi:application
```

**Option 4: In wsgi.py (already configured):**
The `wsgi.py` file is already set to use production settings by default.

## Configuration Files

### `manage.py`
- Default: `sc_download_gate.settings.development`
- Used for: Local development, Django management commands

### `wsgi.py`
- Default: `sc_download_gate.settings.production`
- Used for: Production WSGI server (Gunicorn)

### `asgi.py`
- Default: `sc_download_gate.settings.production`
- Used for: Production ASGI server (if using async features)

## Environment Variables

Both development and production settings use environment variables from `.env` file:

### Development
- `DEBUG` - Not needed (hardcoded to True)
- `SECRET_KEY` - Optional (has default)
- `ALLOWED_HOSTS` - Optional (defaults to localhost)

### Production
- `DEBUG` - Must be False (defaults to False)
- `SECRET_KEY` - **REQUIRED** (generate a new one!)
- `ALLOWED_HOSTS` - **REQUIRED** (e.g., `dmh.bandpassrecords.com`)
- `EMAIL_*` - Required for sending emails
- `SECURE_SSL_REDIRECT` - Set to True with SSL
- `SESSION_COOKIE_SECURE` - Set to True with SSL
- `CSRF_COOKIE_SECURE` - Set to True with SSL

## Switching Between Environments

### Local Development
```bash
# Uses development.py by default
python manage.py runserver

# Or explicitly
python manage.py runserver --settings=sc_download_gate.settings.development
```

### Testing Production Settings Locally
```bash
# Temporarily use production settings
DJANGO_SETTINGS_MODULE=sc_download_gate.settings.production python manage.py runserver

# Or
python manage.py runserver --settings=sc_download_gate.settings.production
```

### Production Deployment
The systemd service and wsgi.py are already configured to use production settings.

## Verification

### Check Current Settings
```bash
python manage.py shell
```

```python
from django.conf import settings
print(f"DEBUG: {settings.DEBUG}")
print(f"Settings module: {settings.SETTINGS_MODULE}")
```

### Test Settings
```bash
# Test development settings
python manage.py check --settings=sc_download_gate.settings.development

# Test production settings
python manage.py check --deploy --settings=sc_download_gate.settings.production
```

## Migration from Old Settings

The old `settings.py` has been backed up as `settings.py.old`. 

If you need to reference it:
```bash
# View old settings
cat sc_download_gate/settings.py.old
```

## Troubleshooting

### ImportError: No module named 'sc_download_gate.settings.development'
- Make sure the `settings/` directory exists
- Check that `__init__.py` exists in the settings directory
- Verify you're in the correct directory

### Settings not loading
- Check `DJANGO_SETTINGS_MODULE` environment variable
- Verify the settings file exists
- Check for syntax errors in settings files

### Production settings not working
- Verify `.env` file exists and has correct values
- Check that `DEBUG=False` in `.env`
- Ensure `ALLOWED_HOSTS` includes your domain
- Verify SSL settings are correct

## Best Practices

1. ✅ **Never commit `.env` file** - It's in `.gitignore`
2. ✅ **Use different `SECRET_KEY` for each environment**
3. ✅ **Test production settings locally** before deploying
4. ✅ **Keep `base.py` clean** - Only common settings
5. ✅ **Document environment-specific settings** in each file
6. ✅ **Use environment variables** for sensitive data


