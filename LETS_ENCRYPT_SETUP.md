# Let's Encrypt SSL Setup Guide

Complete guide for setting up Let's Encrypt SSL certificates for `dmh.bandpassrecords.com`.

## Prerequisites

1. **Domain DNS configured:**
   - `dmh.bandpassrecords.com` must point to your server's IP address
   - DNS propagation may take a few minutes to hours

2. **Server requirements:**
   - Root or sudo access
   - Port 80 (HTTP) must be open and accessible from the internet
   - Nginx installed and running

3. **Verify DNS:**
   ```bash
   dig dmh.bandpassrecords.com
   # or
   nslookup dmh.bandpassrecords.com
   ```
   
   Should return your server's IP address.

## Step-by-Step Setup

### 1. Install Certbot

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
```

**CentOS/RHEL:**
```bash
sudo yum install certbot python3-certbot-nginx
```

**Fedora:**
```bash
sudo dnf install certbot python3-certbot-nginx
```

### 2. Configure Nginx (Basic HTTP First)

Before getting SSL, configure Nginx for HTTP:

```bash
sudo nano /etc/nginx/sites-available/dmh.bandpassrecords.com
```

Add:
```nginx
server {
    listen 80;
    server_name dmh.bandpassrecords.com;

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```

Enable and test:
```bash
sudo ln -s /etc/nginx/sites-available/dmh.bandpassrecords.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Obtain SSL Certificate

Run Certbot:
```bash
sudo certbot --nginx -d dmh.bandpassrecords.com
```

Follow the prompts:
1. **Email address:** Enter your email (for renewal reminders)
2. **Terms of Service:** Type `A` to agree
3. **Share email with EFF:** Your choice (Y or N)
4. **Redirect HTTP to HTTPS:** Type `2` to redirect (recommended)

Certbot will:
- Obtain the certificate
- Automatically configure Nginx with SSL
- Set up automatic renewal

### 4. Verify Certificate

Check certificate status:
```bash
sudo certbot certificates
```

You should see:
```
Found the following certificates:
  Certificate Name: dmh.bandpassrecords.com
    Domains: dmh.bandpassrecords.com
    Expiry Date: YYYY-MM-DD HH:MM:SS+00:00 (VALID: XX days)
    Certificate Path: /etc/letsencrypt/live/dmh.bandpassrecords.com/fullchain.pem
    Private Key Path: /etc/letsencrypt/live/dmh.bandpassrecords.com/privkey.pem
```

### 5. Test Auto-Renewal

Verify automatic renewal works:
```bash
sudo certbot renew --dry-run
```

Expected output:
```
Congratulations, all renewals succeeded. The following certs have been renewed:
  /etc/letsencrypt/live/dmh.bandpassrecords.com/fullchain.pem (success)
```

### 6. Update Django Settings

After SSL is installed, update your `.env` file:

```env
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CSRF_TRUSTED_ORIGINS=https://dmh.bandpassrecords.com
```

Restart your Django application:
```bash
sudo systemctl restart gunicorn
```

## Auto-Renewal

Certbot automatically sets up renewal. Certificates are valid for 90 days and are renewed automatically.

### Check Renewal Status

```bash
# Check if certbot timer is active
sudo systemctl status certbot.timer

# View renewal logs
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

### Manual Renewal (if needed)

```bash
# Renew all certificates
sudo certbot renew

# Renew specific certificate
sudo certbot renew --cert-name dmh.bandpassrecords.com

# Force renewal (even if not expiring)
sudo certbot renew --force-renewal
```

### Renewal Hooks

Add custom commands to run after renewal:

1. **Create deploy hook:**
   ```bash
   sudo nano /etc/letsencrypt/renewal-hooks/deploy/reload-services.sh
   ```

2. **Add commands:**
   ```bash
   #!/bin/bash
   systemctl reload nginx
   systemctl restart gunicorn
   ```

3. **Make executable:**
   ```bash
   sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-services.sh
   ```

## Final Nginx Configuration

After Certbot runs, your Nginx config should look like this:

```nginx
server {
    listen 80;
    server_name dmh.bandpassrecords.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dmh.bandpassrecords.com;

    # Let's Encrypt certificates
    ssl_certificate /etc/letsencrypt/live/dmh.bandpassrecords.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dmh.bandpassrecords.com/privkey.pem;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    client_max_body_size 10M;

    location /static/ {
        alias /path/to/your/project/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /path/to/your/project/media/;
        expires 30d;
    }

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```

## Troubleshooting

### Certificate Not Obtained

**Error: "Failed to obtain certificate"**
- Check DNS: `dig dmh.bandpassrecords.com`
- Verify port 80 is open: `sudo ufw allow 80`
- Check Nginx is running: `sudo systemctl status nginx`
- Verify domain points to server: `curl -I http://dmh.bandpassrecords.com`

**Error: "Connection refused"**
- Ensure Nginx is listening on port 80
- Check firewall: `sudo ufw status`
- Verify server IP matches DNS

### Certificate Not Renewing

**Check renewal logs:**
```bash
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

**Common issues:**
- Port 80 blocked by firewall
- DNS changed
- Nginx configuration error

**Force renewal:**
```bash
sudo certbot renew --force-renewal
```

### Nginx SSL Errors

**"SSL certificate not found"**
```bash
# Verify certificate exists
ls -la /etc/letsencrypt/live/dmh.bandpassrecords.com/

# Check Nginx config
sudo nginx -t

# Verify permissions
sudo chmod 644 /etc/letsencrypt/live/dmh.bandpassrecords.com/fullchain.pem
sudo chmod 600 /etc/letsencrypt/live/dmh.bandpassrecords.com/privkey.pem
```

### Rate Limiting

Let's Encrypt has rate limits:
- 50 certificates per registered domain per week
- 5 duplicate certificates per week

If you hit limits, wait or use staging:
```bash
sudo certbot --nginx -d dmh.bandpassrecords.com --staging
```

## Testing SSL

1. **Test in browser:**
   - Visit: `https://dmh.bandpassrecords.com`
   - Check for padlock icon
   - Verify certificate details

2. **Test with SSL Labs:**
   - Visit: https://www.ssllabs.com/ssltest/
   - Enter: `dmh.bandpassrecords.com`
   - Review SSL rating (aim for A or A+)

3. **Test with command line:**
   ```bash
   openssl s_client -connect dmh.bandpassrecords.com:443 -servername dmh.bandpassrecords.com
   ```

## Security Best Practices

1. ✅ **Always redirect HTTP to HTTPS**
2. ✅ **Use strong SSL protocols** (TLS 1.2+)
3. ✅ **Enable HSTS** (HTTP Strict Transport Security)
4. ✅ **Set secure cookie flags** in Django
5. ✅ **Monitor certificate expiration** (auto-renewal handles this)
6. ✅ **Keep Certbot updated:** `sudo apt upgrade certbot`

## Additional Resources

- Let's Encrypt: https://letsencrypt.org/
- Certbot Documentation: https://certbot.eff.org/
- SSL Labs Test: https://www.ssllabs.com/ssltest/
- Mozilla SSL Configuration Generator: https://ssl-config.mozilla.org/


