# CentOS Stream 10 Setup Guide

Complete setup guide for deploying Django application on CentOS Stream 10.

## Initial Server Setup

### 1. Update System

```bash
sudo dnf update -y
sudo dnf upgrade -y
```

### 2. Install Essential Packages

```bash
# Install development tools
sudo dnf groupinstall -y "Development Tools"
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ make

# Install Git
sudo dnf install -y git

# Install Nginx
sudo dnf install -y nginx

# Install Firewall (firewalld)
sudo dnf install -y firewalld
sudo systemctl enable firewalld
sudo systemctl start firewalld
```

### 3. Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-all
```

### 4. Create Application User (Optional but Recommended)

```bash
# Create a dedicated user for the application
sudo useradd -r -s /bin/bash -d /home/cubase-app -m cubase-app

# Or use existing nginx user (already exists on CentOS)
```

### 5. Set Up Python Virtual Environment

```bash
# Navigate to your project directory
cd /path/to/your/project

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

## Nginx Configuration for CentOS Stream 10

### Important Differences from Ubuntu/Debian

1. **Configuration Location:**
   - CentOS: `/etc/nginx/conf.d/your-site.conf`
   - Ubuntu/Debian: `/etc/nginx/sites-available/` and `/etc/nginx/sites-enabled/`

2. **User/Group:**
   - CentOS: `nginx:nginx`
   - Ubuntu/Debian: `www-data:www-data`

3. **Package Manager:**
   - CentOS: `dnf` (or `yum` on older versions)
   - Ubuntu/Debian: `apt`

### Create Nginx Configuration

```bash
sudo nano /etc/nginx/conf.d/dmh.bandpassrecords.com.conf
```

Add configuration (see PRODUCTION_DEPLOYMENT.md for full config).

### Test and Start Nginx

```bash
# Test configuration
sudo nginx -t

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Check status
sudo systemctl status nginx
```

## Systemd Service Setup

### Create Service File

```bash
sudo nano /etc/systemd/system/daw-macros-hub.service
```

**Important for CentOS:**
- Use `User=nginx` and `Group=nginx` (not www-data)
- Ensure paths are correct
- Include `Environment="DJANGO_SETTINGS_MODULE=sc_download_gate.settings.production"`

### Set Permissions

```bash
# Set ownership of project directory
sudo chown -R nginx:nginx /path/to/your/project

# Set permissions
sudo chmod -R 755 /path/to/your/project
sudo chmod 600 /path/to/your/project/.env

# Create log directory
sudo mkdir -p /var/log/gunicorn
sudo chown nginx:nginx /var/log/gunicorn
```

## SELinux Configuration (CentOS Specific)

CentOS Stream 10 uses SELinux by default. You may need to configure it:

### Check SELinux Status

```bash
sestatus
```

### Allow Nginx to Connect to Gunicorn Socket

```bash
# Allow Nginx to connect to Unix sockets
sudo setsebool -P httpd_can_network_connect 1

# If using custom socket location, set context
sudo semanage fcontext -a -t httpd_sys_rw_content_t "/run/gunicorn.sock"
sudo restorecon -v /run/gunicorn.sock
```

### Allow Nginx to Serve Static Files

```bash
# Set context for static files
sudo semanage fcontext -a -t httpd_sys_content_t "/path/to/your/project/staticfiles(/.*)?"
sudo restorecon -Rv /path/to/your/project/staticfiles

# Set context for media files
sudo semanage fcontext -a -t httpd_sys_rw_content_t "/path/to/your/project/media(/.*)?"
sudo restorecon -Rv /path/to/your/project/media
```

### If SELinux Causes Issues (Temporary)

```bash
# Check SELinux alerts
sudo ausearch -m avc -ts recent

# Temporarily set to permissive (for testing only)
sudo setenforce 0

# Permanently disable (NOT RECOMMENDED for production)
# Edit /etc/selinux/config and set SELINUX=disabled
```

## Let's Encrypt on CentOS Stream 10

### Install Certbot

```bash
# Install EPEL repository
sudo dnf install -y epel-release

# Install Certbot
sudo dnf install -y certbot python3-certbot-nginx

# Verify
certbot --version
```

### Obtain Certificate

```bash
sudo certbot --nginx -d dmh.bandpassrecords.com
```

Certbot will automatically modify your Nginx configuration in `/etc/nginx/conf.d/`.

## File Permissions

### Project Directory

```bash
# Set ownership
sudo chown -R nginx:nginx /path/to/your/project

# Set directory permissions
find /path/to/your/project -type d -exec chmod 755 {} \;

# Set file permissions
find /path/to/your/project -type f -exec chmod 644 {} \;

# Make manage.py executable
chmod +x /path/to/your/project/manage.py

# Protect .env file
chmod 600 /path/to/your/project/.env
```

### Static and Media Files

```bash
# Static files (read-only for Nginx)
sudo chown -R nginx:nginx /path/to/your/project/staticfiles
sudo chmod -R 755 /path/to/your/project/staticfiles

# Media files (read-write for uploads)
sudo chown -R nginx:nginx /path/to/your/project/media
sudo chmod -R 775 /path/to/your/project/media
```

### Logs Directory

```bash
sudo mkdir -p /path/to/your/project/logs
sudo chown nginx:nginx /path/to/your/project/logs
sudo chmod 755 /path/to/your/project/logs
```

## Service Management

### Start Services

```bash
# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Start and enable Django application
sudo systemctl start daw-macros-hub.service
sudo systemctl enable daw-macros-hub.service
```

### Check Status

```bash
# Check Nginx
sudo systemctl status nginx

# Check Django application
sudo systemctl status daw-macros-hub.service

# Check all services
sudo systemctl list-units --type=service --state=running | grep -E 'nginx|cubase'
```

## Troubleshooting CentOS-Specific Issues

### SELinux Denials

```bash
# Check SELinux denials
sudo ausearch -m avc -ts recent

# View detailed logs
sudo sealert -a /var/log/audit/audit.log
```

### Permission Denied Errors

```bash
# Check file ownership
ls -la /path/to/your/project

# Check Nginx user
id nginx

# Verify socket permissions
ls -la /run/gunicorn.sock
```

### Nginx Can't Connect to Gunicorn

```bash
# Check if socket exists
ls -la /run/gunicorn.sock

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Check Gunicorn logs
sudo tail -f /var/log/gunicorn/error.log

# Verify SELinux context
ls -Z /run/gunicorn.sock
```

### Python/Pip Not Found

```bash
# Check Python version
python3 --version

# Check pip
pip3 --version

# If not found, install
sudo dnf install -y python3-pip

# Use python3 and pip3 explicitly
python3 manage.py migrate
pip3 install -r requirements.txt
```

## Useful CentOS Commands

### Package Management

```bash
# Search for package
dnf search package-name

# Install package
sudo dnf install package-name

# Update all packages
sudo dnf update

# Remove package
sudo dnf remove package-name
```

### Service Management

```bash
# List all services
systemctl list-units --type=service

# Check service status
systemctl status service-name

# View service logs
journalctl -u service-name -f
```

### Network Configuration

```bash
# Check IP address
ip addr show

# Check network connectivity
ping -c 4 google.com

# Check listening ports
sudo netstat -tlnp
# or
sudo ss -tlnp
```

## Complete Setup Checklist for CentOS Stream 10

- [ ] System updated (`sudo dnf update`)
- [ ] Python 3 and pip installed
- [ ] Nginx installed and configured
- [ ] Firewall configured (HTTP/HTTPS allowed)
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Database migrations run
- [ ] Static files collected
- [ ] `.env` file created with production values
- [ ] Systemd service created and enabled
- [ ] Nginx configuration created
- [ ] SELinux configured (if enabled)
- [ ] Let's Encrypt certificate installed
- [ ] Services started and enabled
- [ ] Application accessible via browser
- [ ] SSL certificate working
- [ ] Logs being written correctly

## Additional Resources

- CentOS Stream Documentation: https://docs.centos.org/
- Nginx on CentOS: https://nginx.org/en/linux_packages.html
- SELinux Guide: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/using_selinux/
- Firewalld Guide: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_networking/using-and-configuring-firewalld_configuring-and-managing-networking

