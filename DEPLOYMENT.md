# 🚀 Server Deployment Guide

This guide covers deploying the YouTube Video Scraper to a server with automatic GitHub code updates.

## 📋 **Quick Server Setup**

### **Option 1: Automated Setup Script (Recommended)**

1. **Clone and run setup script:**
   ```bash
   git clone https://github.com/pesach/scrape.git
   cd scrape
   chmod +x deploy/setup_server.sh
   sudo ./deploy/setup_server.sh
   ```

2. **Configure environment:**
   ```bash
   sudo nano /etc/environment
   # Add your secrets (see Environment Variables section below)
   ```

3. **Start services:**
   ```bash
   sudo systemctl start youtube-scraper
   sudo systemctl start youtube-worker
   sudo systemctl enable youtube-scraper youtube-worker
   ```

### **Option 2: Manual Setup**

Follow the detailed steps below for complete control over the setup process.

## 🖥️ **Server Requirements**

### **Minimum Specifications:**
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 10GB minimum (videos are temporary)
- **CPU**: 2 cores minimum
- **Network**: Stable internet connection

### **Recommended Cloud Providers:**
- **DigitalOcean**: $12/month droplet (2GB RAM, 2 vCPUs)
- **AWS EC2**: t3.small instance ($15/month)
- **Google Cloud**: e2-small instance ($13/month)
- **Vultr**: $12/month regular performance
- **Linode**: $12/month Nanode

## 🔧 **Step-by-Step Server Setup**

### **Step 1: Server Preparation**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y git python3 python3-pip python3-venv nginx redis-server ffmpeg curl

# Install Docker (optional, for containerized deployment)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### **Step 2: Create Application User**

```bash
# Create dedicated user for the application
sudo useradd -m -s /bin/bash youtube-scraper
sudo usermod -aG docker youtube-scraper

# Switch to application user
sudo su - youtube-scraper
```

### **Step 3: Clone Repository**

```bash
# Clone your repository
git clone https://github.com/pesach/scrape.git
cd scrape

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### **Step 4: Environment Configuration**

```bash
# Create environment file
sudo nano /etc/environment
```

Add your configuration:
```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Backblaze B2 Configuration
B2_APPLICATION_KEY_ID=your_b2_key_id
B2_APPLICATION_KEY=your_b2_application_key
B2_BUCKET_NAME=your-bucket-name
B2_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
APP_WORKERS=4
DOWNLOAD_PATH=/tmp/youtube_downloads
MAX_FILE_SIZE_GB=2
```

### **Step 5: Create Systemd Services**

#### **Web Application Service**
```bash
sudo nano /etc/systemd/system/youtube-scraper.service
```

```ini
[Unit]
Description=YouTube Video Scraper Web Application
After=network.target redis.service

[Service]
Type=simple
User=youtube-scraper
Group=youtube-scraper
WorkingDirectory=/home/youtube-scraper/scrape
Environment=PATH=/home/youtube-scraper/scrape/venv/bin
EnvironmentFile=/etc/environment
ExecStart=/home/youtube-scraper/scrape/venv/bin/python run.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

#### **Celery Worker Service**
```bash
sudo nano /etc/systemd/system/youtube-worker.service
```

```ini
[Unit]
Description=YouTube Video Scraper Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=youtube-scraper
Group=youtube-scraper
WorkingDirectory=/home/youtube-scraper/scrape
Environment=PATH=/home/youtube-scraper/scrape/venv/bin
EnvironmentFile=/etc/environment
ExecStart=/home/youtube-scraper/scrape/venv/bin/python start_worker.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### **Step 6: Nginx Configuration**

```bash
sudo nano /etc/nginx/sites-available/youtube-scraper
```

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Optional: Serve static files directly
    location /static/ {
        alias /home/youtube-scraper/scrape/static/;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/youtube-scraper /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🔄 **Automatic GitHub Updates**

### **Method 1: GitHub Webhooks (Recommended)**

#### **Create Webhook Endpoint**
```bash
sudo nano /home/youtube-scraper/webhook.py
```

```python
#!/usr/bin/env python3
import os
import subprocess
import hmac
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)

# Set this to your GitHub webhook secret
WEBHOOK_SECRET = "your-webhook-secret-here"
REPO_PATH = "/home/youtube-scraper/scrape"

@app.route('/webhook', methods=['POST'])
def github_webhook():
    # Verify webhook signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        return jsonify({'error': 'Invalid signature'}), 403
    
    payload = request.get_json()
    
    # Only deploy on push to main branch
    if payload.get('ref') == 'refs/heads/main':
        try:
            # Pull latest code
            os.chdir(REPO_PATH)
            subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
            
            # Install/update dependencies
            subprocess.run(['./venv/bin/pip', 'install', '-r', 'requirements.txt'], check=True)
            
            # Restart services
            subprocess.run(['sudo', 'systemctl', 'restart', 'youtube-scraper'], check=True)
            subprocess.run(['sudo', 'systemctl', 'restart', 'youtube-worker'], check=True)
            
            return jsonify({'status': 'deployed successfully'})
        except subprocess.CalledProcessError as e:
            return jsonify({'error': f'Deployment failed: {str(e)}'}), 500
    
    return jsonify({'status': 'ignored'})

def verify_signature(payload, signature):
    if not signature:
        return False
    
    expected = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
```

#### **Create Webhook Service**
```bash
sudo nano /etc/systemd/system/github-webhook.service
```

```ini
[Unit]
Description=GitHub Webhook Handler
After=network.target

[Service]
Type=simple
User=youtube-scraper
Group=youtube-scraper
WorkingDirectory=/home/youtube-scraper
ExecStart=/home/youtube-scraper/scrape/venv/bin/python webhook.py
Restart=always

[Install]
WantedBy=multi-user.target
```

#### **Configure GitHub Webhook**
1. Go to your GitHub repository
2. **Settings → Webhooks → Add webhook**
3. **Payload URL**: `http://your-server.com:5000/webhook`
4. **Content type**: `application/json`
5. **Secret**: Set the same secret as in your webhook.py
6. **Events**: Just the push event
7. **Active**: ✅ Checked

### **Method 2: Cron Job Updates**

```bash
# Edit crontab for youtube-scraper user
sudo su - youtube-scraper
crontab -e
```

Add this line to check for updates every 5 minutes:
```bash
*/5 * * * * cd /home/youtube-scraper/scrape && git fetch && [ $(git rev-list HEAD...origin/main --count) != 0 ] && git pull origin main && ./venv/bin/pip install -r requirements.txt && sudo systemctl restart youtube-scraper youtube-worker
```

### **Method 3: Manual Update Script**

```bash
nano /home/youtube-scraper/update.sh
```

```bash
#!/bin/bash
set -e

echo "🔄 Updating YouTube Video Scraper..."

cd /home/youtube-scraper/scrape

# Pull latest code
echo "📥 Pulling latest code from GitHub..."
git pull origin main

# Update dependencies
echo "📦 Updating dependencies..."
./venv/bin/pip install -r requirements.txt

# Run tests
echo "🧪 Running tests..."
./venv/bin/python test_setup.py

# Restart services
echo "🔄 Restarting services..."
sudo systemctl restart youtube-scraper
sudo systemctl restart youtube-worker

echo "✅ Update completed successfully!"

# Check service status
sudo systemctl status youtube-scraper --no-pager
sudo systemctl status youtube-worker --no-pager
```

```bash
chmod +x /home/youtube-scraper/update.sh
```

## 🐳 **Docker Deployment (Alternative)**

### **Using Docker Compose**

```bash
# Clone repository
git clone https://github.com/pesach/scrape.git
cd scrape

# Create environment file
nano .env
# Add your environment variables

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f
```

### **Auto-update with Watchtower**

```yaml
# Add to docker-compose.yml
services:
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_POLL_INTERVAL=300  # Check every 5 minutes
    command: --interval 300
```

## 🔒 **Security Configuration**

### **Firewall Setup**
```bash
# Install and configure UFW
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow necessary ports
sudo ufw allow ssh
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS (if using SSL)
sudo ufw allow 5000/tcp  # Webhook (if using)
```

### **SSL Certificate (Let's Encrypt)**
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (already set up by certbot)
sudo systemctl status certbot.timer
```

### **Environment Security**
```bash
# Secure environment file
sudo chmod 600 /etc/environment
sudo chown root:root /etc/environment

# Secure application directory
sudo chown -R youtube-scraper:youtube-scraper /home/youtube-scraper/scrape
sudo chmod -R 755 /home/youtube-scraper/scrape
```

## 📊 **Monitoring & Maintenance**

### **Service Monitoring**
```bash
# Check service status
sudo systemctl status youtube-scraper
sudo systemctl status youtube-worker
sudo systemctl status redis

# View logs
sudo journalctl -u youtube-scraper -f
sudo journalctl -u youtube-worker -f

# Check application logs
tail -f /home/youtube-scraper/scrape/logs/youtube_scraper.log
```

### **System Monitoring**
```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Monitor system resources
htop
iotop  # Disk I/O
nethogs  # Network usage

# Check disk space
df -h
du -sh /tmp/youtube_downloads/  # Temporary download folder
```

### **Automated Backups**
```bash
# Create backup script
sudo nano /home/youtube-scraper/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/youtube-scraper/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration
cp /etc/environment $BACKUP_DIR/environment_$DATE
cp -r /home/youtube-scraper/scrape $BACKUP_DIR/app_$DATE

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

Add to crontab:
```bash
0 2 * * * /home/youtube-scraper/backup.sh
```

## 🚀 **Performance Optimization**

### **Redis Optimization**
```bash
sudo nano /etc/redis/redis.conf
```

```conf
# Memory optimization
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence (optional, for job recovery)
save 900 1
save 300 10
save 60 10000
```

### **Nginx Optimization**
```bash
sudo nano /etc/nginx/nginx.conf
```

```nginx
http {
    # Enable gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    
    # Connection optimization
    keepalive_timeout 65;
    keepalive_requests 1000;
    
    # Buffer sizes
    client_max_body_size 10M;
    client_body_buffer_size 128k;
}
```

### **System Optimization**
```bash
# Increase file limits
sudo nano /etc/security/limits.conf
```

```conf
youtube-scraper soft nofile 65536
youtube-scraper hard nofile 65536
```

## 🔧 **Troubleshooting**

### **Common Issues**

| Issue | Solution |
|-------|----------|
| Services won't start | Check logs: `sudo journalctl -u youtube-scraper` |
| Permission denied | Fix ownership: `sudo chown -R youtube-scraper:youtube-scraper /home/youtube-scraper/` |
| Out of disk space | Clean temp files: `sudo rm -rf /tmp/youtube_downloads/*` |
| Redis connection failed | Start Redis: `sudo systemctl start redis` |
| Nginx 502 error | Check if app is running: `sudo systemctl status youtube-scraper` |

### **Health Checks**
```bash
# Application health
curl http://localhost:8000/health

# Service status
sudo systemctl is-active youtube-scraper youtube-worker redis nginx

# Resource usage
free -h
df -h
```

## 📋 **Deployment Checklist**

- [ ] Server provisioned with minimum requirements
- [ ] All dependencies installed (Python, Redis, FFmpeg, etc.)
- [ ] Repository cloned and dependencies installed
- [ ] Environment variables configured
- [ ] Systemd services created and enabled
- [ ] Nginx configured and running
- [ ] Firewall configured
- [ ] SSL certificate installed (if using domain)
- [ ] Auto-update mechanism configured
- [ ] Monitoring and logging set up
- [ ] Backup system configured
- [ ] Health checks passing

Your server is now ready to automatically deploy the latest code from GitHub and run your YouTube video scraper! 🎉