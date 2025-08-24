#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_USER="youtube-scraper"
APP_DIR="/home/$APP_USER/scrape"
REPO_URL="https://github.com/pesach/scrape.git"

echo -e "${BLUE}🚀 YouTube Video Scraper - Server Setup Script${NC}"
echo -e "${BLUE}================================================${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root (use sudo)${NC}"
   exit 1
fi

echo -e "${YELLOW}📋 This script will:${NC}"
echo "   • Update system packages"
echo "   • Install dependencies (Python, Redis, FFmpeg, Nginx)"
echo "   • Create application user"
echo "   • Clone repository and set up virtual environment"
echo "   • Create systemd services"
echo "   • Configure Nginx"
echo "   • Set up firewall"
echo ""

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⏹️  Setup cancelled${NC}"
    exit 0
fi

# Step 1: System Update
echo -e "${BLUE}📦 Step 1: Updating system packages...${NC}"
apt update && apt upgrade -y

# Step 2: Install Dependencies
echo -e "${BLUE}🔧 Step 2: Installing dependencies...${NC}"
apt install -y \
    git \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    redis-server \
    ffmpeg \
    curl \
    htop \
    ufw \
    certbot \
    python3-certbot-nginx \
    supervisor

# Install Docker (optional)
echo -e "${BLUE}🐳 Installing Docker (optional)...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo -e "${GREEN}✅ Docker installed${NC}"
else
    echo -e "${GREEN}✅ Docker already installed${NC}"
fi

# Step 3: Create Application User
echo -e "${BLUE}👤 Step 3: Creating application user...${NC}"
if id "$APP_USER" &>/dev/null; then
    echo -e "${GREEN}✅ User $APP_USER already exists${NC}"
else
    useradd -m -s /bin/bash $APP_USER
    usermod -aG docker $APP_USER
    echo -e "${GREEN}✅ Created user: $APP_USER${NC}"
fi

# Step 4: Clone Repository
echo -e "${BLUE}📥 Step 4: Cloning repository...${NC}"
if [ -d "$APP_DIR" ]; then
    echo -e "${YELLOW}⚠️  Directory $APP_DIR already exists. Pulling latest changes...${NC}"
    cd $APP_DIR
    sudo -u $APP_USER git pull origin main
else
    sudo -u $APP_USER git clone $REPO_URL $APP_DIR
fi

cd $APP_DIR

# Step 5: Set up Python Environment
echo -e "${BLUE}🐍 Step 5: Setting up Python environment...${NC}"
sudo -u $APP_USER python3 -m venv venv
sudo -u $APP_USER ./venv/bin/pip install --upgrade pip
sudo -u $APP_USER ./venv/bin/pip install -r requirements.txt

# Step 6: Create Directories
echo -e "${BLUE}📁 Step 6: Creating directories...${NC}"
mkdir -p /tmp/youtube_downloads
chown $APP_USER:$APP_USER /tmp/youtube_downloads
mkdir -p /home/$APP_USER/backups
chown $APP_USER:$APP_USER /home/$APP_USER/backups

# Step 7: Create Systemd Services
echo -e "${BLUE}⚙️  Step 7: Creating systemd services...${NC}"

# Web Application Service
cat > /etc/systemd/system/youtube-scraper.service << EOF
[Unit]
Description=YouTube Video Scraper Web Application
After=network.target redis.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
EnvironmentFile=/etc/environment
ExecStart=$APP_DIR/venv/bin/python run.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Celery Worker Service
cat > /etc/systemd/system/youtube-worker.service << EOF
[Unit]
Description=YouTube Video Scraper Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
EnvironmentFile=/etc/environment
ExecStart=$APP_DIR/venv/bin/python start_worker.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Step 8: Configure Nginx
echo -e "${BLUE}🌐 Step 8: Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/youtube-scraper << EOF
server {
    listen 80;
    server_name _;  # Replace with your domain

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }

    # Static files (if any)
    location /static/ {
        alias $APP_DIR/static/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/youtube-scraper /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default  # Remove default site

# Test Nginx configuration
nginx -t

# Step 9: Configure Services
echo -e "${BLUE}🔄 Step 9: Configuring services...${NC}"

# Start and enable Redis
systemctl start redis-server
systemctl enable redis-server

# Start and enable Nginx
systemctl start nginx
systemctl enable nginx

# Reload systemd and enable our services
systemctl daemon-reload
systemctl enable youtube-scraper
systemctl enable youtube-worker

# Step 10: Configure Firewall
echo -e "${BLUE}🔒 Step 10: Configuring firewall...${NC}"
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS

# Step 11: Create Update Script
echo -e "${BLUE}🔄 Step 11: Creating update script...${NC}"
cat > /home/$APP_USER/update.sh << 'EOF'
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
EOF

chmod +x /home/$APP_USER/update.sh
chown $APP_USER:$APP_USER /home/$APP_USER/update.sh

# Step 12: Create Backup Script
echo -e "${BLUE}💾 Step 12: Creating backup script...${NC}"
cat > /home/$APP_USER/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/youtube-scraper/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration
cp /etc/environment $BACKUP_DIR/environment_$DATE 2>/dev/null || echo "No environment file to backup"
cp -r /home/youtube-scraper/scrape $BACKUP_DIR/app_$DATE

# Keep only last 7 days of backups
find $BACKUP_DIR -type d -name "app_*" -mtime +7 -exec rm -rf {} + 2>/dev/null || true
find $BACKUP_DIR -type f -name "environment_*" -mtime +7 -delete 2>/dev/null || true

echo "Backup completed: $DATE"
EOF

chmod +x /home/$APP_USER/backup.sh
chown $APP_USER:$APP_USER /home/$APP_USER/backup.sh

# Add backup to crontab
(sudo -u $APP_USER crontab -l 2>/dev/null; echo "0 2 * * * /home/$APP_USER/backup.sh") | sudo -u $APP_USER crontab -

# Step 13: Create Environment Template
echo -e "${BLUE}⚙️  Step 13: Creating environment template...${NC}"
cat > /etc/environment.template << EOF
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
EOF

# Set permissions
chmod 600 /etc/environment.template

# Step 14: Final Setup
echo -e "${BLUE}🎯 Step 14: Final setup...${NC}"

# Create log directory
mkdir -p $APP_DIR/logs
chown -R $APP_USER:$APP_USER $APP_DIR

# Set proper permissions
chown -R $APP_USER:$APP_USER /home/$APP_USER
chmod -R 755 $APP_DIR

echo -e "${GREEN}✅ Server setup completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Configure environment variables:"
echo "   sudo cp /etc/environment.template /etc/environment"
echo "   sudo nano /etc/environment"
echo ""
echo "2. Start the services:"
echo "   sudo systemctl start youtube-scraper"
echo "   sudo systemctl start youtube-worker"
echo ""
echo "3. Check service status:"
echo "   sudo systemctl status youtube-scraper"
echo "   sudo systemctl status youtube-worker"
echo ""
echo "4. Test the application:"
echo "   curl http://localhost/health"
echo ""
echo "5. View logs:"
echo "   sudo journalctl -u youtube-scraper -f"
echo ""
echo -e "${BLUE}📖 For detailed configuration, see DEPLOYMENT.md${NC}"
echo -e "${BLUE}🧪 For testing instructions, see TESTING.md${NC}"
echo ""
echo -e "${GREEN}🎉 Your YouTube Video Scraper server is ready!${NC}"