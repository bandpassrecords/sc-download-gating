# Google Authentication Setup Guide

This guide explains how to set up Google OAuth authentication for your Django application using django-allauth.

## Prerequisites

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run migrations:**
```bash
python manage.py migrate
```

This will create the necessary database tables for django-allauth.

## Step 1: Create Google OAuth Credentials

1. **Go to Google Cloud Console:**
   - Visit https://console.cloud.google.com/
   - Sign in with your Google account

2. **Create a New Project (or select existing):**
   - Click on the project dropdown at the top
   - Click "New Project"
   - Enter project name: "DAW Macros Hub" (or your preferred name)
   - Click "Create"

3. **Enable Google+ API:**
   - In the left sidebar, go to "APIs & Services" > "Library"
   - Search for "Google+ API"
   - Click on it and click "Enable"

4. **Create OAuth 2.0 Credentials:**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - If prompted, configure the OAuth consent screen first:
     - User Type: External (for public use) or Internal (for organization only)
     - App name: "DAW Macros Hub"
     - User support email: Your email
     - Developer contact: Your email
     - Click "Save and Continue"
     - Scopes: Click "Save and Continue" (default scopes are fine)
     - Test users: Add your email if using External type, then "Save and Continue"
     - Click "Back to Dashboard"

5. **Create OAuth Client ID:**
   - Application type: "Web application"
   - Name: "DAW Macros Hub Web Client"
   - Authorized JavaScript origins:
     - For development: `http://127.0.0.1:8000`
     - For production: `https://yourdomain.com`
   - Authorized redirect URIs:
     - For development: `http://127.0.0.1:8000/accounts/google/login/callback/`
     - For production: `https://yourdomain.com/accounts/google/login/callback/`
   - Click "Create"
   - **Copy the Client ID and Client Secret** (you'll need these!)

## Step 2: Configure Django Settings

### Option A: Environment Variables (Recommended)

1. **Create/update `.env` file** in your project root:
```env
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
```

2. **Update `settings.py`** to use environment variables:
```python
from decouple import config

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
```

### Option B: Direct Configuration (Not Recommended for Production)

Update `settings.py` directly:
```python
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
            'client_id': 'your-client-id-here.apps.googleusercontent.com',
            'secret': 'your-client-secret-here',
            'key': ''
        }
    }
}
```

## Step 3: Update Site Domain

1. **Access Django Admin:**
   - Go to `http://127.0.0.1:8000/admin/`
   - Log in with your admin account

2. **Update Site Settings:**
   - Go to "Sites" > "Sites"
   - Click on the default site (usually "example.com")
   - Update:
     - Domain name: `127.0.0.1:8000` (for development) or `yourdomain.com` (for production)
     - Display name: "DAW Macros Hub"
   - Click "Save"

## Step 4: Test the Integration

1. **Start your Django server:**
```bash
python manage.py runserver
```

2. **Test Google Login:**
   - Go to `http://127.0.0.1:8000/accounts/login/`
   - You should see a "Continue with Google" button
   - Click it and test the OAuth flow

## Troubleshooting

### "Redirect URI mismatch" Error

This means the redirect URI in your Google OAuth credentials doesn't match what Django is using.

**Solution:**
1. Go to Google Cloud Console > Credentials
2. Edit your OAuth 2.0 Client ID
3. Add the exact redirect URI: `http://127.0.0.1:8000/accounts/google/login/callback/`
4. Make sure there are no trailing slashes or extra characters

### "Invalid Client" Error

This means your Client ID or Client Secret is incorrect.

**Solution:**
1. Double-check your `.env` file or settings.py
2. Make sure there are no extra spaces
3. Verify the credentials in Google Cloud Console

### "Access Blocked" Error

This usually means the OAuth consent screen isn't properly configured.

**Solution:**
1. Go to Google Cloud Console > OAuth consent screen
2. Make sure all required fields are filled
3. If using "External" user type, add test users
4. Publish the app (if ready for production)

### Users Not Being Created

Check that:
1. `SOCIALACCOUNT_AUTO_SIGNUP = True` in settings.py
2. Migrations have been run: `python manage.py migrate`
3. Site ID is set correctly: `SITE_ID = 1`

## Production Deployment

For production, make sure to:

1. **Update Authorized Redirect URIs:**
   - Add your production domain: `https://yourdomain.com/accounts/google/login/callback/`

2. **Use Environment Variables:**
   - Never commit credentials to version control
   - Use environment variables or a secrets management service

3. **Update Site Domain:**
   - In Django Admin, update the Site domain to your production domain

4. **Publish OAuth Consent Screen:**
   - In Google Cloud Console, go to OAuth consent screen
   - Click "Publish App" when ready
   - Note: This may require verification for certain scopes

5. **Enable Additional Security:**
   - Consider enabling 2FA for your Google account
   - Regularly rotate OAuth credentials
   - Monitor OAuth usage in Google Cloud Console

## Additional Providers

To add more social providers (Facebook, GitHub, etc.), install additional packages and add them to `SOCIALACCOUNT_PROVIDERS` in settings.py.

Example for GitHub:
```python
'github': {
    'APP': {
        'client_id': config('GITHUB_CLIENT_ID', default=''),
        'secret': config('GITHUB_CLIENT_SECRET', default=''),
    }
}
```

Then add `'allauth.socialaccount.providers.github'` to `INSTALLED_APPS`.


