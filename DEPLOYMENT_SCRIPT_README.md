# Production Deployment Script

This script automates the production deployment process for CentOS Stream 10.

## Prerequisites

1. **Root or sudo access** - The script needs root privileges to install packages and configure services
2. **.env file** - Must exist in the project directory with all necessary configuration
3. **Domain DNS** - Domain should point to the server's IP address (for SSL certificate)

## Quick Start

1. **Make script executable:**
   ```bash
   chmod +x deploy_production.sh
   ```

2. **Run the script:**
   ```bash
   sudo ./deploy_production.sh
   ```

3. **Follow the prompts:**
   - The script will ask for confirmation (y/n) at each step
   - Enter the project directory path when prompted
   - Enter virtual environment directory (or use default)
   - Enter domain name (or use default: dmh.bandpassrecords.com)
   - Enter number of Gunicorn workers (or use default: 3)

## What the Script Does

The script performs the following steps (each with user confirmation):

1. **System Updates** - Updates all system packages
2. **Install Dependencies** - Installs Python, Nginx, Git, and other required packages
3. **Configure Firewall** - Sets up firewalld to allow HTTP and HTTPS
4. **Setup Virtual Environment** - Creates Python virtual environment
5. **Install Python Dependencies** - Installs packages from requirements.txt
6. **Run Migrations** - Executes Django database migrations
7. **Collect Static Files** - Collects static files for production
8. **Create Systemd Service** - Creates and enables Gunicorn service
9. **Configure Nginx** - Creates Nginx configuration file
10. **Setup SSL** - Installs Certbot and obtains Let's Encrypt certificate
11. **Set Permissions** - Configures file ownership and permissions
12. **Configure SELinux** - Sets up SELinux contexts (CentOS specific)
13. **Start Services** - Starts Nginx and Django application
14. **Create Superuser** - Optionally creates Django admin user

## Configuration

### Before Running

Make sure your `.env` file contains all necessary variables:

```env
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=dmh.bandpassrecords.com
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=info@bandpassrecords.com
SERVER_EMAIL=info@bandpassrecords.com
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CSRF_TRUSTED_ORIGINS=https://dmh.bandpassrecords.com
DJANGO_LOG_LEVEL=INFO
```

### Script Variables

You can modify these variables at the top of the script:

- `DOMAIN` - Your domain name (default: dmh.bandpassrecords.com)
- `SERVICE_USER` - User to run the service (default: nginx)
- `SERVICE_GROUP` - Group to run the service (default: nginx)
- `GUNICORN_WORKERS` - Number of Gunicorn workers (default: 3)

## Interactive Prompts

The script will ask for confirmation at each step:

```
Step 1: System Updates
Update system packages (y/n): y
```

You can:
- Type `y` or `yes` to proceed
- Type `n` or `no` to skip
- Press Enter to see the prompt again

## What Gets Created

### Files and Directories

- `/etc/systemd/system/daw-macros-hub.service` - Systemd service file
- `/etc/nginx/conf.d/dmh.bandpassrecords.com.conf` - Nginx configuration
- `/var/log/gunicorn/` - Gunicorn log directory
- `$PROJECT_DIR/venv/` - Python virtual environment (if created)
- `$PROJECT_DIR/staticfiles/` - Collected static files
- `$PROJECT_DIR/logs/` - Application logs directory

### Services

- `daw-macros-hub.service` - Django application service (enabled for auto-start)
- `nginx.service` - Nginx web server (enabled for auto-start)
- `firewalld.service` - Firewall service (enabled)

## Troubleshooting

### Script Fails at a Step

If the script fails, you can:
1. Fix the issue manually
2. Re-run the script - it will skip steps that are already completed
3. Or run individual steps manually

### Check Service Status

```bash
# Check Django application
sudo systemctl status daw-macros-hub.service

# Check Nginx
sudo systemctl status nginx

# View logs
sudo journalctl -u daw-macros-hub.service -f
sudo tail -f /var/log/gunicorn/error.log
sudo tail -f /var/log/nginx/error.log
```

### Restart Services

```bash
# Restart Django application
sudo systemctl restart daw-macros-hub.service

# Restart Nginx
sudo systemctl restart nginx
```

### SSL Certificate Issues

If SSL certificate generation fails:
1. Make sure domain DNS points to server IP
2. Make sure port 80 is accessible
3. Run manually: `sudo certbot --nginx -d dmh.bandpassrecords.com`

### Permission Issues

If you encounter permission errors:
```bash
# Fix ownership
sudo chown -R nginx:nginx /path/to/project

# Fix permissions
sudo chmod 755 /path/to/project
sudo chmod 600 /path/to/project/.env
```

### SELinux Issues

If SELinux blocks access:
```bash
# Check SELinux status
getenforce

# View SELinux denials
sudo ausearch -m avc -ts recent

# Temporarily set to permissive (for testing)
sudo setenforce 0
```

## Manual Steps After Deployment

1. **Update Django Site Domain:**
   - Go to: https://dmh.bandpassrecords.com/admin/
   - Navigate to Sites > Sites
   - Update domain name to: `dmh.bandpassrecords.com`

2. **Test Application:**
   - Visit: https://dmh.bandpassrecords.com
   - Test user registration
   - Test login/logout
   - Test file uploads

3. **Monitor Logs:**
   ```bash
   # Application logs
   tail -f /path/to/project/logs/django.log
   
   # Gunicorn logs
   tail -f /var/log/gunicorn/error.log
   
   # Nginx logs
   tail -f /var/log/nginx/error.log
   ```

## Updating the Application

After making code changes:

```bash
# 1. Pull latest code
cd /path/to/project
git pull

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install new dependencies (if any)
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Restart service
sudo systemctl restart daw-macros-hub.service
```

## Security Notes

- The script sets proper file permissions
- .env file is set to 600 (read/write for owner only)
- Services run as non-root user (nginx)
- SELinux is configured (if enabled)
- Firewall is configured to allow only HTTP/HTTPS

## Support

For issues or questions:
- Check the logs: `/var/log/gunicorn/error.log`
- Check service status: `sudo systemctl status daw-macros-hub.service`
- Review deployment guides: `PRODUCTION_DEPLOYMENT.md` and `CENTOS_STREAM_10_SETUP.md`


