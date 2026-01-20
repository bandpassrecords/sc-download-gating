#!/bin/bash

###############################################################################
# Production Deployment Script for CentOS Stream 10
# sc_download_gate - Django Application (side-by-side deployment)
#
# NOTE:
# This script is designed to deploy alongside other apps already running
# on the server (e.g. daw-cubase / daw-macros-hub) by using:
# - a dedicated systemd service name
# - a dedicated RuntimeDirectory/socket path
# - dedicated gunicorn log files
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables (will be prompted)
PROJECT_DIR=""
VENV_DIR=""
DOMAIN="download.bandpassrecords.com"
SERVICE_USER="nginx"
SERVICE_GROUP="nginx"
GUNICORN_WORKERS=3
DB_NAME="sc_download_gate"
DB_USER="sc_download_gate"
DB_PASSWORD=""
DB_HOST="localhost"
DB_PORT="5432"

# Side-by-side deployment identifiers (avoid conflicts with existing apps)
SERVICE_NAME="sc-download-gate"
RUNTIME_DIR="gunicorn-sc-download-gate"
GUNICORN_SOCKET="/run/${RUNTIME_DIR}/gunicorn.sock"
GUNICORN_ACCESS_LOG="/var/log/gunicorn/${SERVICE_NAME}-access.log"
GUNICORN_ERROR_LOG="/var/log/gunicorn/${SERVICE_NAME}-error.log"

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

confirm() {
    local prompt="$1"
    local response
    while true; do
        read -p "$(echo -e ${YELLOW}"$prompt (y/n): "${NC})" response
        case $response in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

check_root() {
    if [ "$EUID" -ne 0 ]; then 
        print_error "Please run as root or with sudo"
        exit 1
    fi
}

check_env_file() {
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        print_error ".env file not found at $PROJECT_DIR/.env"
        print_info "Please create the .env file with all necessary configuration before running this script"
        exit 1
    fi
    print_success ".env file found"
}

###############################################################################
# Step 1: System Updates
###############################################################################

step_system_update() {
    print_header "Step 1: System Updates"
    
    if confirm "Update system packages"; then
        print_info "Updating system packages..."
        dnf update -y
        print_success "System packages updated"
    else
        print_warning "Skipping system update"
    fi
}

###############################################################################
# Step 2: Install System Dependencies
###############################################################################

step_install_dependencies() {
    print_header "Step 2: Install System Dependencies"
    
    if confirm "Install system dependencies (Python, Nginx, Git, etc.)"; then
        print_info "Installing system dependencies..."
        
        # Install development tools
        dnf groupinstall -y "Development Tools" || print_warning "Development Tools group already installed"
        
        # Install Python and dependencies
        dnf install -y python3 python3-pip python3-devel gcc gcc-c++ make
        
        # Install PostgreSQL development libraries (needed for psycopg2)
        dnf install -y postgresql-devel
        
        # Install Git
        dnf install -y git
        
        # Install Nginx
        dnf install -y nginx
        
        # Install Firewalld
        dnf install -y firewalld
        
        print_success "System dependencies installed"
    else
        print_warning "Skipping dependency installation"
    fi
}

###############################################################################
# Step 3: Configure Firewall
###############################################################################

step_configure_firewall() {
    print_header "Step 3: Configure Firewall"
    
    if confirm "Configure firewall (firewalld) to allow HTTP, HTTPS, and SMTP"; then
        print_info "Configuring firewall..."
        
        systemctl enable firewalld
        systemctl start firewalld
        
        # Web server ports
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        
        # SMTP port for email sending
        print_info "Adding SMTP port 587 for email functionality..."
        firewall-cmd --permanent --add-port=587/tcp  # SMTP with TLS
        
        firewall-cmd --reload
        
        print_success "Firewall configured"
        print_info "Opened ports:"
        echo "  - HTTP (80)"
        echo "  - HTTPS (443)"
        echo "  - SMTP TLS (587) - for email sending"
        print_info "Current firewall rules:"
        firewall-cmd --list-all
    else
        print_warning "Skipping firewall configuration"
    fi
}

###############################################################################
# Step 4: Setup Python Virtual Environment
###############################################################################

step_setup_venv() {
    print_header "Step 4: Setup Python Virtual Environment"
    
    if [ -z "$VENV_DIR" ]; then
        VENV_DIR="$PROJECT_DIR/venv"
    fi
    
    if [ -d "$VENV_DIR" ]; then
        print_warning "Virtual environment already exists at $VENV_DIR"
        if confirm "Recreate virtual environment (this will delete the existing one)"; then
            rm -rf "$VENV_DIR"
        else
            print_info "Using existing virtual environment"
            return 0
        fi
    fi
    
    if confirm "Create Python virtual environment at $VENV_DIR"; then
        print_info "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        print_success "Virtual environment created"
        
        print_info "Upgrading pip..."
        "$VENV_DIR/bin/pip" install --upgrade pip
        print_success "Pip upgraded"
    else
        print_warning "Skipping virtual environment creation"
    fi
}

###############################################################################
# Step 5: Install Python Dependencies
###############################################################################

step_install_python_deps() {
    print_header "Step 5: Install Python Dependencies"
    
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found at $VENV_DIR"
        return 1
    fi
    
    if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
        print_error "requirements.txt not found at $PROJECT_DIR/requirements.txt"
        return 1
    fi
    
    if confirm "Install Python dependencies from requirements.txt"; then
        print_info "Installing Python dependencies..."
        "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
        print_success "Python dependencies installed"
    else
        print_warning "Skipping Python dependencies installation"
    fi
}

###############################################################################
# Step 6: Install and Configure PostgreSQL
###############################################################################

step_install_postgresql() {
    print_header "Step 6: Install and Configure PostgreSQL"
    
    if confirm "Install and configure PostgreSQL database"; then
        print_info "Installing PostgreSQL..."
        
        # Install PostgreSQL server and client
        dnf install -y postgresql-server postgresql-contrib
        
        # Initialize PostgreSQL database if not already initialized
        if [ ! -d "/var/lib/pgsql/data" ] || [ -z "$(ls -A /var/lib/pgsql/data 2>/dev/null)" ]; then
            print_info "Initializing PostgreSQL database..."
            postgresql-setup --initdb
            print_success "PostgreSQL database initialized"
        else
            print_info "PostgreSQL database already initialized"
        fi
        
        # Start and enable PostgreSQL
        systemctl enable postgresql
        systemctl start postgresql
        
        print_success "PostgreSQL installed and started"
        
        # Create database and user
        if confirm "Create PostgreSQL database and user for the application"; then
            print_info "Creating database and user..."
            
            # Get database credentials
            if [ -z "$DB_PASSWORD" ]; then
                read -sp "Enter PostgreSQL password for user '$DB_USER': " DB_PASSWORD
                echo ""
                read -sp "Confirm password: " DB_PASSWORD_CONFIRM
                echo ""
                
                if [ "$DB_PASSWORD" != "$DB_PASSWORD_CONFIRM" ]; then
                    print_error "Passwords do not match"
                    return 1
                fi
            fi
            
            # Create database and user using psql
            sudo -u postgres psql << EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    ELSE
        ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges on database
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Connect to the new database and grant schema privileges
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
\q
EOF
            
            if [ $? -eq 0 ]; then
                print_success "Database and user created successfully"
                print_info "Database name: $DB_NAME"
                print_info "Database user: $DB_USER"
                print_info "Database host: $DB_HOST"
                print_info "Database port: $DB_PORT"
                
                # Update .env file with database settings
                if [ -f "$PROJECT_DIR/.env" ]; then
                    print_info "Updating .env file with database settings..."
                    
                    # Remove old database settings if they exist
                    sed -i '/^DATABASE_URL=/d' "$PROJECT_DIR/.env"
                    sed -i '/^DB_NAME=/d' "$PROJECT_DIR/.env"
                    sed -i '/^DB_USER=/d' "$PROJECT_DIR/.env"
                    sed -i '/^DB_PASSWORD=/d' "$PROJECT_DIR/.env"
                    sed -i '/^DB_HOST=/d' "$PROJECT_DIR/.env"
                    sed -i '/^DB_PORT=/d' "$PROJECT_DIR/.env"
                    
                    # Add new database settings
                    cat >> "$PROJECT_DIR/.env" << EOF

# PostgreSQL Database Configuration
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
EOF
                    
                    print_success ".env file updated with database settings"
                else
                    print_warning ".env file not found, you'll need to add database settings manually"
                fi
            else
                print_error "Failed to create database and user"
                return 1
            fi
        else
            print_warning "Skipping database and user creation"
            print_info "You can create them manually with:"
            echo "  sudo -u postgres psql"
            echo "  CREATE USER $DB_USER WITH PASSWORD 'your_password';"
            echo "  CREATE DATABASE $DB_NAME OWNER $DB_USER;"
            echo "  GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
        fi
        
        # Configure PostgreSQL for remote/local connections (if needed)
        if confirm "Configure PostgreSQL to allow local password authentication"; then
            print_info "Configuring PostgreSQL authentication..."
            
            PG_HBA="/var/lib/pgsql/data/pg_hba.conf"
            
            # Backup original file
            cp "$PG_HBA" "${PG_HBA}.backup"
            print_success "Backed up pg_hba.conf to ${PG_HBA}.backup"
            
            # Replace ident authentication with md5 for local connections
            # This allows password authentication from localhost
            sed -i 's/^\(local[[:space:]]*all[[:space:]]*all[[:space:]]*\)ident/\1md5/' "$PG_HBA"
            sed -i 's/^\(host[[:space:]]*all[[:space:]]*all[[:space:]]*127\.0\.0\.1\/32[[:space:]]*\)ident/\1md5/' "$PG_HBA"
            sed -i 's/^\(host[[:space:]]*all[[:space:]]*all[[:space:]]*::1\/128[[:space:]]*\)ident/\1md5/' "$PG_HBA"
            
            # Add specific user rules if not present (for extra security)
            if ! grep -q "^local.*all.*$DB_USER.*md5" "$PG_HBA"; then
                # Add before the default rules
                sed -i "/^# TYPE/a local   all             $DB_USER                                md5" "$PG_HBA"
            fi
            
            if ! grep -q "^host.*all.*$DB_USER.*127.0.0.1/32.*md5" "$PG_HBA"; then
                sed -i "/^# IPv4 local connections:/a host    all             $DB_USER            127.0.0.1/32            md5" "$PG_HBA"
            fi
            
            if ! grep -q "^host.*all.*$DB_USER.*::1/128.*md5" "$PG_HBA"; then
                sed -i "/^# IPv6 local connections:/a host    all             $DB_USER            ::1/128                 md5" "$PG_HBA"
            fi
            
            # Reload PostgreSQL configuration
            systemctl reload postgresql
            
            if [ $? -eq 0 ]; then
                print_success "PostgreSQL authentication configured successfully"
                print_info "Changed authentication from 'ident' to 'md5' for local connections"
            else
                print_error "Failed to reload PostgreSQL. Please check the configuration manually."
                print_info "You may need to restart PostgreSQL: sudo systemctl restart postgresql"
            fi
        fi
    else
        print_warning "Skipping PostgreSQL installation"
        print_info "Make sure PostgreSQL is installed and configured manually"
    fi
}

###############################################################################
# Step 7: Run Database Migrations
###############################################################################

step_run_migrations() {
    print_header "Step 7: Run Database Migrations"
    
    if confirm "Run Django database migrations"; then
        print_info "Running migrations..."
        cd "$PROJECT_DIR"
        "$VENV_DIR/bin/python" manage.py migrate
        print_success "Database migrations completed"
    else
        print_warning "Skipping database migrations"
    fi
}

###############################################################################
# Step 8: Configure Django Site
###############################################################################

step_configure_site() {
    print_header "Step 7: Configure Django Site"
    
    if confirm "Configure Django Site object (required for email links and allauth)"; then
        print_info "Configuring Site object..."
        cd "$PROJECT_DIR"
        
        # Use Python to update the Site object
        "$VENV_DIR/bin/python" << EOF
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sc_download_gate.settings.production')
django.setup()

from django.contrib.sites.models import Site

try:
    site = Site.objects.get(id=1)  # SITE_ID = 1
    old_domain = site.domain
    old_name = site.name
    
    site.domain = '$DOMAIN'
    site.name = 'DAW Macros Hub'
    site.save()
    
    print(f"Site updated successfully!")
    print(f"  Domain: {old_domain} -> {site.domain}")
    print(f"  Name: {old_name} -> {site.name}")
except Site.DoesNotExist:
    print("Creating new Site object...")
    site = Site.objects.create(
        id=1,
        domain='$DOMAIN',
        name='DAW Macros Hub'
    )
    print(f"Site created successfully!")
    print(f"  Domain: {site.domain}")
    print(f"  Name: {site.name}")
except Exception as e:
    print(f"Error configuring Site: {e}")
    exit(1)
EOF
        
        if [ $? -eq 0 ]; then
            print_success "Django Site configured"
            print_info "Site domain: $DOMAIN"
            print_info "Site name: DAW Macros Hub"
        else
            print_error "Failed to configure Django Site"
            print_warning "You may need to configure it manually in Django admin or shell"
        fi
    else
        print_warning "Skipping Site configuration"
        print_info "You can configure it later with:"
        echo "  python manage.py shell"
        echo "  from django.contrib.sites.models import Site"
        echo "  site = Site.objects.get(id=1)"
        echo "  site.domain = '$DOMAIN'"
        echo "  site.name = 'DAW Macros Hub'"
        echo "  site.save()"
    fi
}

###############################################################################
# Step 9: Collect Static Files
###############################################################################

step_collect_static() {
    print_header "Step 8: Collect Static Files"
    
    if confirm "Collect static files for production"; then
        print_info "Collecting static files..."
        cd "$PROJECT_DIR"
        
        # Create static directory if it doesn't exist (prevents warnings)
        if [ ! -d "$PROJECT_DIR/static" ]; then
            mkdir -p "$PROJECT_DIR/static"
            print_info "Created static directory"
        fi
        
        # Create staticfiles directory if it doesn't exist
        if [ ! -d "$PROJECT_DIR/staticfiles" ]; then
            mkdir -p "$PROJECT_DIR/staticfiles"
            print_info "Created staticfiles directory"
        fi
        
        "$VENV_DIR/bin/python" manage.py collectstatic --noinput
        print_success "Static files collected"
    else
        print_warning "Skipping static files collection"
    fi
}

###############################################################################
# Step 10: Create Systemd Service
###############################################################################

step_create_systemd_service() {
    print_header "Step 9: Create Systemd Service"
    
    if confirm "Create systemd service for Gunicorn"; then
        print_info "Creating systemd service file..."
        
        # Create log directory
        mkdir -p /var/log/gunicorn
        chown "$SERVICE_USER:$SERVICE_GROUP" /var/log/gunicorn
        chmod 755 /var/log/gunicorn
        
        # Ensure socket directory exists and is accessible
        # /run is typically tmpfs, but we ensure it's there
        if [ ! -d "/run" ]; then
            mkdir -p /run
        fi
        
        # Create service file (dedicated, does not touch existing apps)
        SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
        
        # Use RuntimeDirectory for better systemd integration
        # This creates /run/${RUNTIME_DIR}/ with proper permissions
        cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Gunicorn daemon for sc_download_gate Django application
After=network.target

[Service]
Type=notify
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="DJANGO_SETTINGS_MODULE=sc_download_gate.settings.production"
EnvironmentFile=$PROJECT_DIR/.env
RuntimeDirectory=$RUNTIME_DIR
RuntimeDirectoryMode=0755
UMask=0007
ExecStart=$VENV_DIR/bin/gunicorn \\
    --workers $GUNICORN_WORKERS \\
    --bind unix:${GUNICORN_SOCKET} \\
    --access-logfile ${GUNICORN_ACCESS_LOG} \\
    --error-logfile ${GUNICORN_ERROR_LOG} \\
    --timeout 120 \\
    --graceful-timeout 30 \\
    sc_download_gate.wsgi:application

Restart=always
RestartSec=3
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
        
        print_success "Systemd service file created at $SERVICE_FILE"
        
        # Verify .env file is accessible before proceeding
        if [ ! -r "$PROJECT_DIR/.env" ]; then
            print_error ".env file is not readable by current user"
            print_info "Setting ownership of .env file..."
            chown "$SERVICE_USER:$SERVICE_GROUP" "$PROJECT_DIR/.env"
            chmod 600 "$PROJECT_DIR/.env"
        fi
        
        # Reload systemd
        systemctl daemon-reload
        print_success "Systemd daemon reloaded"
        
        # Enable service
        if confirm "Enable service to start on boot"; then
            systemctl enable "${SERVICE_NAME}.service"
            print_success "Service enabled for auto-start"
        fi
    else
        print_warning "Skipping systemd service creation"
    fi
}

###############################################################################
# Step 11: Configure Nginx
###############################################################################

step_configure_nginx() {
    print_header "Step 10: Configure Nginx"
    
    if confirm "Create Nginx configuration for $DOMAIN"; then
        print_info "Creating Nginx configuration..."
        
        NGINX_CONF="/etc/nginx/conf.d/${DOMAIN}.conf"
        
        cat > "$NGINX_CONF" << EOF
# HTTP server
# Certbot will modify this to redirect to HTTPS and create the HTTPS server block
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 10M;

    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 30d;
    }

    location / {
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_pass http://unix:${GUNICORN_SOCKET};
    }
}
EOF
        
        print_success "Nginx configuration created at $NGINX_CONF"
        
        # Test Nginx configuration
        if nginx -t; then
            print_success "Nginx configuration test passed"
        else
            print_error "Nginx configuration test failed"
            return 1
        fi
    else
        print_warning "Skipping Nginx configuration"
    fi
}

###############################################################################
# Step 12: Setup Let's Encrypt SSL
###############################################################################

step_setup_ssl() {
    print_header "Step 11: Setup Let's Encrypt SSL Certificate"
    
    if confirm "Install and configure Let's Encrypt SSL certificate"; then
        print_info "Installing Certbot..."
        
        # Install EPEL repository
        dnf install -y epel-release
        
        # Install Certbot
        dnf install -y certbot python3-certbot-nginx
        
        print_success "Certbot installed"
        
        if confirm "Obtain SSL certificate for $DOMAIN (requires domain to point to this server)"; then
            print_info "Obtaining SSL certificate..."
            print_warning "Make sure $DOMAIN points to this server's IP address"
            print_warning "Make sure port 80 is accessible from the internet"
            
            if confirm "Continue with certificate generation"; then
                certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "$(grep DEFAULT_FROM_EMAIL "$PROJECT_DIR/.env" | cut -d '=' -f2 || echo 'admin@example.com')"
                
                if [ $? -eq 0 ]; then
                    print_success "SSL certificate obtained and configured"
                    
                    # Test auto-renewal
                    if confirm "Test SSL certificate auto-renewal"; then
                        certbot renew --dry-run
                        print_success "Auto-renewal test completed"
                    fi
                else
                    print_error "Failed to obtain SSL certificate"
                    print_info "You can run 'certbot --nginx -d $DOMAIN' manually later"
                fi
            else
                print_warning "Skipping SSL certificate generation"
                print_info "You can run 'certbot --nginx -d $DOMAIN' manually later"
            fi
        else
            print_warning "Skipping SSL certificate generation"
        fi
    else
        print_warning "Skipping SSL setup"
    fi
}

###############################################################################
# Step 13: Set File Permissions
###############################################################################

step_set_permissions() {
    print_header "Step 13: Set File Permissions"
    
    if confirm "Set proper file permissions for project directory"; then
        print_info "Setting file permissions..."
        
        # Set ownership of project directory
        chown -R "$SERVICE_USER:$SERVICE_GROUP" "$PROJECT_DIR"
        
        # Set directory permissions (readable and executable by owner and group)
        find "$PROJECT_DIR" -type d -exec chmod 755 {} \;
        
        # Set file permissions (readable by owner and group)
        find "$PROJECT_DIR" -type f -exec chmod 644 {} \;
        
        # Make manage.py executable
        chmod +x "$PROJECT_DIR/manage.py"
        
        # .env file: owned by nginx, readable only by owner (600)
        chown "$SERVICE_USER:$SERVICE_GROUP" "$PROJECT_DIR/.env"
        chmod 600 "$PROJECT_DIR/.env"
        
        # Virtual environment: ensure nginx can access it
        if [ -d "$VENV_DIR" ]; then
            chown -R "$SERVICE_USER:$SERVICE_GROUP" "$VENV_DIR"
            find "$VENV_DIR" -type d -exec chmod 755 {} \;
            find "$VENV_DIR" -type f -exec chmod 644 {} \;
            # Make Python and scripts executable
            find "$VENV_DIR/bin" -type f -exec chmod 755 {} \;
        fi
        
        # Static files
        if [ -d "$PROJECT_DIR/staticfiles" ]; then
            chown -R "$SERVICE_USER:$SERVICE_GROUP" "$PROJECT_DIR/staticfiles"
            chmod -R 755 "$PROJECT_DIR/staticfiles"
        fi
        
        # Media files
        if [ -d "$PROJECT_DIR/media" ]; then
            chown -R "$SERVICE_USER:$SERVICE_GROUP" "$PROJECT_DIR/media"
            chmod -R 775 "$PROJECT_DIR/media"
        fi
        
        # Logs directory
        mkdir -p "$PROJECT_DIR/logs"
        chown "$SERVICE_USER:$SERVICE_GROUP" "$PROJECT_DIR/logs"
        chmod 755 "$PROJECT_DIR/logs"
        
        # Socket directory: ensure /run is accessible and create socket with proper permissions
        # The socket will be created by gunicorn, but we need to ensure the directory is accessible
        if [ ! -d "/run" ]; then
            mkdir -p /run
        fi
        # Note: /run is typically a tmpfs, so we can't chown it, but gunicorn will create the socket
        
        print_success "File permissions set"
        print_info "Verifying .env file permissions..."
        ls -la "$PROJECT_DIR/.env" || print_warning ".env file not found or not accessible"
    else
        print_warning "Skipping permission setup"
    fi
}

###############################################################################
# Step 14: Configure SELinux (CentOS Specific)
###############################################################################

step_configure_selinux() {
    print_header "Step 14: Configure SELinux (CentOS Specific)"
    
    if [ -f /usr/sbin/getenforce ]; then
        SELINUX_STATUS=$(getenforce)
        print_info "Current SELinux status: $SELINUX_STATUS"
        
        if [ "$SELINUX_STATUS" != "Disabled" ]; then
            if confirm "Configure SELinux for Nginx and Gunicorn"; then
                print_info "Configuring SELinux..."
                
                # Allow Nginx to connect to network
                setsebool -P httpd_can_network_connect 1
                
                # Set context for static files
                if [ -d "$PROJECT_DIR/staticfiles" ]; then
                    semanage fcontext -a -t httpd_sys_content_t "$PROJECT_DIR/staticfiles(/.*)?" 2>/dev/null || true
                    restorecon -Rv "$PROJECT_DIR/staticfiles"
                fi
                
                # Set context for media files
                if [ -d "$PROJECT_DIR/media" ]; then
                    semanage fcontext -a -t httpd_sys_rw_content_t "$PROJECT_DIR/media(/.*)?" 2>/dev/null || true
                    restorecon -Rv "$PROJECT_DIR/media"
                fi
                
                print_success "SELinux configured"
                print_info "If you encounter permission issues, check SELinux logs: sudo ausearch -m avc -ts recent"
            else
                print_warning "Skipping SELinux configuration"
            fi
        else
            print_info "SELinux is disabled, skipping configuration"
        fi
    else
        print_info "SELinux not installed, skipping configuration"
    fi
}

###############################################################################
# Step 15: Start Services
###############################################################################

step_start_services() {
    print_header "Step 15: Start Services"
    
    if confirm "Start and enable PostgreSQL service"; then
        if systemctl is-active --quiet postgresql; then
            print_warning "PostgreSQL is already running"
        else
            systemctl start postgresql
            systemctl enable postgresql
            print_success "PostgreSQL started and enabled"
        fi
    fi
    
    if confirm "Start and enable Nginx service"; then
        # Check if nginx is already running
        if systemctl is-active --quiet nginx; then
            print_warning "Nginx is already running"
            if confirm "Stop and restart Nginx"; then
                systemctl stop nginx
                sleep 2
            else
                print_info "Skipping Nginx start (already running)"
                systemctl enable nginx
                return 0
            fi
        fi
        
        # Check if ports 80 or 443 are in use
        if command -v ss >/dev/null 2>&1; then
            PORT80_IN_USE=$(ss -tuln | grep -c ':80 ' || true)
            PORT443_IN_USE=$(ss -tuln | grep -c ':443 ' || true)
        elif command -v netstat >/dev/null 2>&1; then
            PORT80_IN_USE=$(netstat -tuln | grep -c ':80 ' || true)
            PORT443_IN_USE=$(netstat -tuln | grep -c ':443 ' || true)
        else
            PORT80_IN_USE=0
            PORT443_IN_USE=0
        fi
        
        if [ "$PORT80_IN_USE" -gt 0 ] || [ "$PORT443_IN_USE" -gt 0 ]; then
            print_error "Ports 80 or 443 are already in use"
            print_info "Checking what's using these ports..."
            
            if command -v ss >/dev/null 2>&1; then
                print_info "Processes using port 80:"
                ss -tulpn | grep ':80 ' || true
                print_info "Processes using port 443:"
                ss -tulpn | grep ':443 ' || true
            elif command -v netstat >/dev/null 2>&1; then
                print_info "Processes using port 80:"
                netstat -tulpn | grep ':80 ' || true
                print_info "Processes using port 443:"
                netstat -tulpn | grep ':443 ' || true
            fi
            
            print_warning "You need to stop the process using these ports before starting Nginx"
            print_info "Common solutions:"
            echo "  1. If another nginx is running: sudo systemctl stop nginx"
            echo "  2. If Apache is running: sudo systemctl stop httpd"
            echo "  3. Find and kill the process: sudo lsof -i :80 -i :443"
            
            if confirm "Try to stop any existing nginx/httpd processes automatically"; then
                systemctl stop nginx 2>/dev/null || true
                systemctl stop httpd 2>/dev/null || true
                sleep 2
            else
                print_error "Cannot start Nginx with ports in use. Please resolve manually."
                return 1
            fi
        fi
        
        # Try to start nginx
        if systemctl start nginx; then
            systemctl enable nginx
            systemctl status nginx --no-pager -l
            print_success "Nginx started and enabled"
        else
            print_error "Failed to start Nginx"
            print_info "Check the error with: sudo systemctl status nginx"
            print_info "Or view logs: sudo journalctl -xeu nginx.service"
            return 1
        fi
    fi
    
    if confirm "Start Django application service (Gunicorn)"; then
        if systemctl start "${SERVICE_NAME}.service"; then
            systemctl status "${SERVICE_NAME}.service" --no-pager -l
            print_success "Django application service started"
        else
            print_error "Failed to start Django application service"
            print_info "Check the error with: sudo systemctl status ${SERVICE_NAME}.service"
            return 1
        fi
    fi
}

###############################################################################
# Step 16: Create Superuser (Optional)
###############################################################################

step_create_superuser() {
    print_header "Step 16: Create Django Superuser (Optional)"
    
    if confirm "Create Django superuser account"; then
        cd "$PROJECT_DIR"
        "$VENV_DIR/bin/python" manage.py createsuperuser
        print_success "Superuser creation completed"
    else
        print_info "Skipping superuser creation"
        print_info "You can create one later with: python manage.py createsuperuser"
    fi
}

###############################################################################
# Main Execution
###############################################################################

main() {
    print_header "sc_download_gate - Production Deployment Script"
    print_info "This script will guide you through the production deployment process"
    print_info "Make sure you have the .env file ready with all necessary configuration"
    echo ""
    
    # Check if running as root
    check_root
    
    # Get project directory
    if [ -z "$PROJECT_DIR" ]; then
        read -p "Enter project directory path (e.g., /opt/sc-download-gate): " PROJECT_DIR
    fi
    
    # Validate project directory
    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "Project directory not found: $PROJECT_DIR"
        exit 1
    fi
    
    PROJECT_DIR=$(realpath "$PROJECT_DIR")
    print_success "Project directory: $PROJECT_DIR"
    
    # Check for .env file
    check_env_file
    
    # Get virtual environment directory
    read -p "Enter virtual environment directory (default: $PROJECT_DIR/venv): " VENV_INPUT
    VENV_DIR="${VENV_INPUT:-$PROJECT_DIR/venv}"
    VENV_DIR=$(realpath "$VENV_DIR" 2>/dev/null || echo "$VENV_DIR")
    
    # Get domain
    read -p "Enter domain name (default: $DOMAIN): " DOMAIN_INPUT
    DOMAIN="${DOMAIN_INPUT:-$DOMAIN}"
    
    # Get number of workers
    read -p "Enter number of Gunicorn workers (default: $GUNICORN_WORKERS): " WORKERS_INPUT
    GUNICORN_WORKERS="${WORKERS_INPUT:-$GUNICORN_WORKERS}"
    
    # Get database configuration
    read -p "Enter PostgreSQL database name (default: $DB_NAME): " DB_NAME_INPUT
    DB_NAME="${DB_NAME_INPUT:-$DB_NAME}"
    
    read -p "Enter PostgreSQL database user (default: $DB_USER): " DB_USER_INPUT
    DB_USER="${DB_USER_INPUT:-$DB_USER}"
    
    read -p "Enter PostgreSQL database host (default: $DB_HOST): " DB_HOST_INPUT
    DB_HOST="${DB_HOST_INPUT:-$DB_HOST}"
    
    read -p "Enter PostgreSQL database port (default: $DB_PORT): " DB_PORT_INPUT
    DB_PORT="${DB_PORT_INPUT:-$DB_PORT}"
    
    echo ""
    print_info "Configuration Summary:"
    echo "  Project Directory: $PROJECT_DIR"
    echo "  Virtual Environment: $VENV_DIR"
    echo "  Domain: $DOMAIN"
    echo "  Gunicorn Workers: $GUNICORN_WORKERS"
    echo "  Service User: $SERVICE_USER"
    echo "  Database Name: $DB_NAME"
    echo "  Database User: $DB_USER"
    echo "  Database Host: $DB_HOST"
    echo "  Database Port: $DB_PORT"
    echo ""
    
    if ! confirm "Continue with deployment using these settings"; then
        print_info "Deployment cancelled"
        exit 0
    fi
    
    # Execute deployment steps
    step_system_update
    step_install_dependencies
    step_configure_firewall
    step_setup_venv
    step_install_python_deps
    step_install_postgresql
    step_run_migrations
    step_configure_site
    step_collect_static
    step_create_systemd_service
    step_configure_nginx
    step_setup_ssl
    step_set_permissions
    step_configure_selinux
    step_start_services
    step_create_superuser
    
    # Final summary
    print_header "Deployment Complete!"
    print_success "Your application should now be running!"
    echo ""
    print_info "Next steps:"
    echo "  1. Visit https://$DOMAIN to verify the application"
    echo "  2. Check service status: sudo systemctl status ${SERVICE_NAME}.service"
    echo "  3. Check Nginx status: sudo systemctl status nginx"
    echo "  4. Check PostgreSQL status: sudo systemctl status postgresql"
    echo "  5. View application logs: sudo tail -f ${GUNICORN_ERROR_LOG}"
    echo "  6. View Nginx logs: sudo tail -f /var/log/nginx/error.log"
    echo ""
    print_info "Useful commands:"
    echo "  Restart application: sudo systemctl restart ${SERVICE_NAME}.service"
    echo "  Restart Nginx: sudo systemctl restart nginx"
    echo "  Restart PostgreSQL: sudo systemctl restart postgresql"
    echo "  View service logs: sudo journalctl -u ${SERVICE_NAME}.service -f"
    echo "  View PostgreSQL logs: sudo tail -f /var/lib/pgsql/data/log/postgresql-*.log"
    echo ""
}

# Run main function
main

