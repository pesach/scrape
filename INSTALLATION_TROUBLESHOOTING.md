# 🛠️ Installation Troubleshooting Guide

This guide helps resolve common installation issues with the YouTube Video Scraper.

## ⚡ **Quick Fix for psycopg2-binary Error**

If you're getting `psycopg2-binary` subprocess errors, **skip that dependency entirely**:

```bash
# Use this instead of requirements.txt
pip install -r requirements-no-postgres.txt
```

**Why this works:** This project uses Supabase's HTTP API, so you don't need direct PostgreSQL drivers!

## 🐍 **Python Dependencies Issues**

### **Issue: `psycopg2-binary` Build Error**

```bash
error: failed building wheel for psycopg2-binary
subprocess-exited-with-error
```

**This is a subprocess/compilation error, not a pip issue. Here are multiple solutions:**

#### **Solution 1: Install System Dependencies First**

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3-dev libpq-dev build-essential
pip install -r requirements.txt
```

**CentOS/RHEL/Fedora:**
```bash
sudo yum install python3-devel postgresql-devel gcc
# or on newer versions:
sudo dnf install python3-devel postgresql-devel gcc
pip install -r requirements.txt
```

**macOS:**
```bash
# Install Xcode command line tools
xcode-select --install

# Install PostgreSQL (includes libpq)
brew install postgresql

pip install -r requirements.txt
```

#### **Solution 2: Skip PostgreSQL Dependencies (Recommended)**

```bash
# Use requirements file without psycopg2-binary
pip install -r requirements-no-postgres.txt
```

**Why this works:** The Supabase client handles PostgreSQL connections internally via HTTP API, so you don't actually need `psycopg2-binary` for this project!

#### **Solution 3: Use Alternative Requirements File**

```bash
# Use the alternative requirements without psycopg2-binary
pip install -r requirements-alternative.txt

# Then install one of these PostgreSQL adapters:

# Option A: Standard psycopg2 (requires PostgreSQL dev headers)
pip install psycopg2==2.9.9

# Option B: Pure Python alternative (no compilation needed)
pip install asyncpg==0.29.0
```

#### **Solution 4: Use Pre-compiled Wheels**

```bash
# Upgrade pip and use pre-compiled wheels
pip install --upgrade pip wheel
pip install --only-binary=psycopg2-binary psycopg2-binary
pip install -r requirements.txt
```

#### **Solution 5: Docker Installation (Always Works)**

If you're having persistent issues, use Docker:

```bash
# Build and run with Docker
docker-compose up --build
```

This avoids all system dependency issues!

## 🔧 **System Dependencies**

### **FFmpeg Installation**

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**CentOS/RHEL:**
```bash
sudo yum install epel-release
sudo yum install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
1. Download from https://ffmpeg.org/download.html
2. Add to PATH environment variable

### **Redis Installation**

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
- Download Redis from https://redis.io/download
- Or use Docker: `docker run -d -p 6379:6379 redis:alpine`

## 🐳 **Docker Alternative (Easiest)**

If you're having dependency issues, Docker is the easiest solution:

### **Quick Docker Setup:**

```bash
# Clone the repository
git clone https://github.com/pesach/scrape.git
cd scrape

# Create environment file
cp .env.example .env
# Edit .env with your actual values

# Start everything with Docker
docker-compose up -d

# Check logs
docker-compose logs -f
```

**Benefits of Docker:**
- ✅ No dependency issues
- ✅ Consistent environment
- ✅ Easy deployment
- ✅ Includes Redis, Python, FFmpeg automatically

## 🔍 **Testing Your Installation**

### **Quick Dependency Test:**

```bash
# Test Python imports
python -c "import yt_dlp; print('✅ yt-dlp OK')"
python -c "import fastapi; print('✅ FastAPI OK')"
python -c "import supabase; print('✅ Supabase OK')"
python -c "import boto3; print('✅ Boto3 OK')"
python -c "import celery; print('✅ Celery OK')"
python -c "import redis; print('✅ Redis OK')"

# Test system dependencies
ffmpeg -version | head -1
redis-cli ping
```

### **Full Setup Test:**

```bash
# Run the comprehensive test
python test_setup.py
```

## 🌐 **Environment-Specific Solutions**

### **GitHub Codespaces / Cloud IDEs**

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y postgresql-dev python3-dev build-essential ffmpeg redis-server

# Start Redis
sudo service redis-server start

# Install Python packages
pip install -r requirements.txt
```

### **Windows (WSL2 Recommended)**

```bash
# In WSL2 Ubuntu
sudo apt update
sudo apt install python3-pip python3-dev libpq-dev build-essential ffmpeg redis-server
pip install -r requirements.txt
```

### **Virtual Environments**

```bash
# Create clean virtual environment
python -m venv youtube_scraper_env
source youtube_scraper_env/bin/activate  # Linux/macOS
# or
youtube_scraper_env\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip wheel setuptools

# Install dependencies
pip install -r requirements.txt
```

## 🚨 **Common Error Solutions**

### **Error: `Microsoft Visual C++ 14.0 is required`** (Windows)

**Solution:**
1. Install Visual Studio Build Tools
2. Or use pre-compiled wheels: `pip install --only-binary=all -r requirements.txt`
3. Or use Docker

### **Error: `command 'gcc' failed`** (Linux)

**Solution:**
```bash
sudo apt-get install build-essential python3-dev
# or
sudo yum groupinstall "Development Tools"
```

### **Error: `pg_config executable not found`**

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install libpq-dev

# CentOS/RHEL
sudo yum install postgresql-devel

# macOS
brew install postgresql
```

### **Error: `Redis connection refused`**

**Solution:**
```bash
# Check if Redis is running
redis-cli ping

# If not, start it:
sudo systemctl start redis-server  # Linux
brew services start redis          # macOS

# Or use Docker Redis:
docker run -d -p 6379:6379 redis:alpine
```

## 📋 **Installation Checklist**

- [ ] **Python 3.8+** installed
- [ ] **pip** upgraded to latest version
- [ ] **System dependencies** installed (build tools, PostgreSQL dev headers)
- [ ] **FFmpeg** installed and in PATH
- [ ] **Redis** installed and running
- [ ] **Virtual environment** created (recommended)
- [ ] **Python packages** installed successfully
- [ ] **Environment variables** configured
- [ ] **Database schema** applied to Supabase
- [ ] **Test setup** passes all checks

## 🆘 **Still Having Issues?**

### **Option 1: Use Docker (Recommended)**
```bash
docker-compose up --build
```

### **Option 2: Use GitHub Codespaces**
- Fork the repository on GitHub
- Open in Codespaces
- Dependencies install automatically

### **Option 3: Use Repl.it or Similar**
- Import the repository
- Cloud environment handles dependencies

### **Option 4: Manual Step-by-Step**
```bash
# 1. Clean install
pip uninstall -y -r requirements.txt
pip cache purge

# 2. Install system dependencies first
# (see platform-specific instructions above)

# 3. Install Python packages one by one
pip install fastapi uvicorn
pip install yt-dlp
pip install supabase
pip install boto3
pip install celery redis
# ... etc
```

**Remember: Docker is often the easiest solution if you're having persistent dependency issues!** 🐳