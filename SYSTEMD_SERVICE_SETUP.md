# Systemd Service Setup Guide

This guide explains how to set up a systemd service to automatically start your Django application when the system boots.

## Prerequisites

1. Gunicorn installed in your virtual environment
2. Project directory accessible
3. User/group permissions configured
4. Log directory created

## Step-by-Step Setup

### 1. Create Log Directory

```bash
sudo mkdir -p /var/log/gunicorn
sudo chown www-data:www-data /var/log/gunicorn
```

### 2. Create Systemd Service File

Copy the service file template:

```bash
sudo nano /etc/systemd/system/daw-macros-hub.service
```

Or use the provided template and update paths:

```bash
# Copy the template
sudo cp gunicorn.service /etc/systemd/system/daw-macros-hub.service

# Edit with your actual paths
sudo nano /etc/systemd/system/daw-macros-hub.service
```

### 3. Update Service File Paths

Edit `/etc/systemd/system/daw-macros-hub.service` and update:

- **WorkingDirectory:** Full path to your project (e.g., `/home/user/daw-macros-hub/daw-macros-hub`)
- **Environment PATH:** Path to your virtual environment's bin directory (e.g., `/home/user/venv/bin`)
- **ExecStart:** Full path to gunicorn in your venv (e.g., `/home/user/venv/bin/gunicorn`)
- **User/Group:** Your server user (commonly `www-data` for Ubuntu/Debian, `nginx` for CentOS)

**Example configuration:**
```ini
[Unit]
Description=Gunicorn daemon for SoundCloud Download Gating By BandPass Records Django application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/home/user/daw-macros-hub/daw-macros-hub
Environment="PATH=/home/user/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=sc_download_gate.settings.production"
EnvironmentFile=/home/user/daw-macros-hub/daw-macros-hub/.env
ExecStart=/home/user/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/run/gunicorn.sock \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    sc_download_gate.wsgi:application

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

**Key points:**
- `EnvironmentFile` loads your `.env` file (optional but recommended)
- `Restart=always` ensures the service restarts if it crashes
- `RestartSec=3` waits 3 seconds before restarting
- `After=network.target` ensures network is available before starting

### 4. Reload Systemd

```bash
sudo systemctl daemon-reload
```

### 5. Enable Service (Start on Boot)

```bash
sudo systemctl enable daw-macros-hub.service
```

### 6. Start the Service

```bash
sudo systemctl start daw-macros-hub.service
```

### 7. Check Service Status

```bash
sudo systemctl status daw-macros-hub.service
```

You should see:
```
● daw-macros-hub.service - Gunicorn daemon for SoundCloud Download Gating By BandPass Records Django application
     Loaded: loaded (/etc/systemd/system/daw-macros-hub.service; enabled; vendor preset: enabled)
     Active: active (running) since ...
```

### 8. Verify It's Running

```bash
# Check if socket file exists
ls -la /run/gunicorn.sock

# Check process
ps aux | grep gunicorn

# Check logs
sudo tail -f /var/log/gunicorn/error.log
```

## Service Management Commands

### Start Service
```bash
sudo systemctl start daw-macros-hub.service
```

### Stop Service
```bash
sudo systemctl stop daw-macros-hub.service
```

### Restart Service
```bash
sudo systemctl restart daw-macros-hub.service
```

### Reload Service (graceful restart)
```bash
sudo systemctl reload daw-macros-hub.service
```

### Check Status
```bash
sudo systemctl status daw-macros-hub.service
```

### View Logs
```bash
# Service logs
sudo journalctl -u daw-macros-hub.service -f

# Gunicorn access logs
sudo tail -f /var/log/gunicorn/access.log

# Gunicorn error logs
sudo tail -f /var/log/gunicorn/error.log
```

### Disable Auto-Start
```bash
sudo systemctl disable daw-macros-hub.service
```

## Advanced Configuration

### Environment Variables

To load environment variables from `.env` file:

```ini
[Service]
EnvironmentFile=/path/to/your/project/.env
```

Or set specific variables:

```ini
[Service]
Environment="DJANGO_SETTINGS_MODULE=sc_download_gate.settings"
Environment="PYTHONPATH=/path/to/your/project"
```

### Multiple Workers

Adjust worker count based on CPU cores:

```ini
ExecStart=/path/to/venv/bin/gunicorn \
    --workers 4 \
    --threads 2 \
    --worker-class gthread \
    ...
```

**Worker calculation:**
- CPU-bound: `(2 × CPU cores) + 1`
- I/O-bound: `(4 × CPU cores) + 1`

### Timeout Settings

```ini
ExecStart=/path/to/venv/bin/gunicorn \
    --timeout 120 \
    --graceful-timeout 30 \
    ...
```

### User Permissions

If using a different user:

```bash
# Create a dedicated user
sudo useradd -r -s /bin/false cubase-app

# Set ownership
sudo chown -R cubase-app:cubase-app /path/to/your/project

# Update service file
User=cubase-app
Group=cubase-app
```

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
sudo journalctl -u daw-macros-hub.service -n 50
```

**Common issues:**
- Wrong paths in service file
- Missing permissions
- Port already in use
- Database connection issues
- Missing environment variables

### Permission Denied

```bash
# Check file permissions
ls -la /path/to/your/project

# Fix ownership
sudo chown -R www-data:www-data /path/to/your/project

# Check socket permissions
ls -la /run/gunicorn.sock
```

### Socket File Not Created

```bash
# Check if service is running
sudo systemctl status daw-macros-hub.service

# Check Gunicorn logs
sudo tail -f /var/log/gunicorn/error.log

# Verify socket path in service file
```

### Service Crashes on Startup

**Check error logs:**
```bash
sudo journalctl -u daw-macros-hub.service --since "10 minutes ago"
```

**Common causes:**
- Import errors
- Database connection failed
- Missing dependencies
- Incorrect settings

### Test Configuration

Before enabling, test the command manually:

```bash
cd /path/to/your/project
source /path/to/venv/bin/activate
gunicorn --workers 3 --bind unix:/run/gunicorn.sock sc_download_gate.wsgi:application
```

If this works, the service should work too.

## Integration with Nginx

Make sure Nginx is configured to use the socket:

```nginx
location / {
    proxy_pass http://unix:/run/gunicorn.sock;
    ...
}
```

And ensure Nginx starts after Gunicorn:

```ini
[Unit]
After=network.target
Wants=network-online.target
```

## Cron Jobs (Optional)

For periodic tasks (database backups, cleanup, etc.):

### 1. Edit Crontab

```bash
sudo crontab -e
```

### 2. Add Cron Jobs

**Daily database backup:**
```cron
0 2 * * * /path/to/venv/bin/python /path/to/project/manage.py dumpdata > /path/to/backups/db_$(date +\%Y\%m\%d).json
```

**Weekly cleanup:**
```cron
0 3 * * 0 /path/to/venv/bin/python /path/to/project/manage.py clearsessions
```

**Daily log rotation:**
```cron
0 1 * * * find /var/log/gunicorn -name "*.log" -mtime +30 -delete
```

### 3. Django Management Commands

Create custom management commands for scheduled tasks:

```python
# macros/management/commands/daily_cleanup.py
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Daily cleanup tasks'

    def handle(self, *args, **options):
        # Your cleanup logic here
        self.stdout.write(self.style.SUCCESS('Cleanup completed'))
```

Then add to crontab:
```cron
0 4 * * * /path/to/venv/bin/python /path/to/project/manage.py daily_cleanup
```

## Complete Example Service File

```ini
[Unit]
Description=Gunicorn daemon for SoundCloud Download Gating By BandPass Records Django application
After=network.target postgresql.service
Wants=network-online.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/home/user/daw-macros-hub/daw-macros-hub
Environment="PATH=/home/user/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=sc_download_gate.settings"
EnvironmentFile=/home/user/daw-macros-hub/daw-macros-hub/.env

ExecStart=/home/user/venv/bin/gunicorn \
    --workers 3 \
    --threads 2 \
    --worker-class gthread \
    --bind unix:/run/gunicorn.sock \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    --log-level info \
    --env DJANGO_SETTINGS_MODULE=sc_download_gate.settings.production \
    sc_download_gate.wsgi:application

ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

## Security Considerations

1. **File Permissions:**
   ```bash
   # Restrict service file
   sudo chmod 644 /etc/systemd/system/daw-macros-hub.service
   
   # Protect .env file
   chmod 600 /path/to/project/.env
   ```

2. **Run as Non-Root:**
   - Always use a non-root user (www-data, nginx, etc.)
   - Limit file permissions

3. **Log Rotation:**
   ```bash
   sudo nano /etc/logrotate.d/gunicorn
   ```
   
   Add:
   ```
   /var/log/gunicorn/*.log {
       daily
       missingok
       rotate 14
       compress
       delaycompress
       notifempty
       create 0640 www-data www-data
       sharedscripts
       postrotate
           systemctl reload daw-macros-hub.service > /dev/null 2>&1 || true
       endscript
   }
   ```

## Verification Checklist

- [ ] Service file created and paths updated
- [ ] Log directory created with proper permissions
- [ ] Service enabled for auto-start
- [ ] Service starts successfully
- [ ] Socket file created at `/run/gunicorn.sock`
- [ ] Nginx can connect to socket
- [ ] Application accessible via web browser
- [ ] Service restarts automatically on crash
- [ ] Service starts on system boot
- [ ] Logs are being written correctly

