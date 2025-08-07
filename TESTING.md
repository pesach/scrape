# 🧪 Testing Guide for YouTube Video Scraper

This document provides comprehensive testing instructions for the YouTube Video Scraper system.

## 📋 **Quick Testing Checklist**

- [ ] GitHub secrets configured
- [ ] Test workflow passes
- [ ] Local verification script succeeds  
- [ ] Setup test passes all components
- [ ] Health endpoints return success
- [ ] Simple demo works for metadata extraction
- [ ] Database schema applied to Supabase

## 🔐 **GitHub Secrets Testing**

### **Step 1: Add Secrets to GitHub**

1. Go to your repository on GitHub
2. Navigate to: **Settings → Secrets and variables → Actions**
3. Click **"New repository secret"**
4. Add each of these secrets with the **exact names**:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
B2_APPLICATION_KEY_ID=005a1b2c3d4e5f6789abcdef
B2_APPLICATION_KEY=K005abcdef1234567890...
B2_BUCKET_NAME=my-youtube-videos
B2_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
```

**Important Notes:**
- Secret names are **case-sensitive**
- Use the Supabase **anon/public key**, not service_role key
- B2 endpoint URL should match your bucket's region

### **Step 2: Run Automated Test Workflow**

1. **Push your code to GitHub**:
   ```bash
   git add -A
   git commit -m "Configure GitHub secrets"
   git push origin main
   ```

2. **Trigger the test workflow**:
   - Go to **Repository → Actions**
   - Find **"Test GitHub Secrets Configuration"**
   - Click **"Run workflow"**
   - Click **"Run workflow"** again to confirm

3. **Monitor the results**:
   - Each step should show a green checkmark ✅
   - If any step fails ❌, click on it to see the error details

### **Step 3: Interpret Test Results**

| Test Step | What It Checks | If It Fails |
|-----------|----------------|-------------|
| **Configuration Loading** | All secrets present and valid format | Check secret names and values in GitHub |
| **Database Connection** | Supabase URL and key work | Verify Supabase URL and use anon key |
| **B2 Configuration** | Backblaze credentials valid | Check B2 key ID, key, bucket name, endpoint |
| **YouTube Parser** | yt-dlp can extract metadata | Usually passes if dependencies install correctly |

## 🖥️ **Local Testing**

### **Verification Script**

```bash
python verify_secrets.py
```

This script will:
- Show expected secret formats with examples
- Validate any secrets you have set locally
- Provide step-by-step setup instructions
- Guide you to the test workflow

**Sample Output:**
```
🔐 GitHub Secrets Verification Tool
==================================================
🔍 Checking GitHub Secrets Format...

📋 Required GitHub Repository Secrets:
==================================================

🔑 SUPABASE_URL
   Description: Supabase project URL
   Example: https://your-project.supabase.co
   Status: ⚪ Not set locally (expected in GitHub)

🔑 SUPABASE_KEY
   Description: Supabase anon/public key
   Example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   Status: ⚪ Not set locally (expected in GitHub)
```

### **Component Testing**

Test individual components to isolate issues:

```bash
# Test configuration system
python -c "from config import config; print('✅ Config loaded')"

# Test database connection (requires secrets)
python -c "from database import db; print('✅ Database ready')"

# Test B2 storage (requires secrets)
python -c "from storage import storage; print('✅ B2 storage ready')"

# Test YouTube parser (no secrets needed)
python -c "from youtube_parser import parse_youtube_url; print('✅ Parser ready')"
```

### **Setup Test**

```bash
python test_setup.py
```

This comprehensive test checks:
- ✅ Python package imports (yt-dlp, FastAPI, etc.)
- ✅ Environment variables/configuration
- ✅ Redis connection
- ✅ FFmpeg availability  
- ✅ YouTube URL parsing functionality

**Sample Output:**
```
🧪 YouTube Video Scraper - Setup Verification

🔍 Testing imports...
  ✅ yt-dlp
  ✅ FastAPI
  ✅ Celery
  ✅ Supabase
  ✅ Boto3
  ✅ Redis

🔧 Testing environment variables...
  ✅ SUPABASE_URL
  ✅ SUPABASE_KEY
  [... etc]

📊 Test Results: 5/5 tests passed
🎉 All tests passed! Your setup is ready.
```

## 🌐 **Application Testing**

### **Simple Metadata Demo**

Test YouTube metadata extraction without external dependencies:

```bash
python simple_demo.py
```

- Opens test server at `http://localhost:8001`
- Provides a web interface to test URL parsing
- Tests only yt-dlp functionality
- Good for isolating YouTube-related issues

**Test URLs:**
- `https://www.youtube.com/watch?v=dQw4w9WgXcQ` (single video)
- `https://www.youtube.com/channel/UCefarW8iWzuNO7NedV-om-w` (channel)
- `https://www.youtube.com/playlist?list=PLrAXtmRdnEQy8VbX6gf_1bSC6WcqDi8Wq` (playlist)

### **Full Application Testing**

Once your secrets are configured:

```bash
# Start the main application
python run.py
```

**Health Check Endpoints:**

```bash
# Overall system health
curl http://localhost:8000/health

# Configuration debug info
curl http://localhost:8000/debug

# Queue status and load monitoring
curl http://localhost:8000/api/queue-status
```

**Expected Responses:**

**Health Endpoint (`/health`):**
```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "youtube_parser": "healthy",
    "celery": "available",
    "environment": "configured"
  }
}
```

**Debug Endpoint (`/debug`):**
```json
{
  "configuration": {
    "supabase_configured": true,
    "b2_configured": true,
    "environment": "development"
  },
  "environment_variables": {
    "SUPABASE_URL": "✅",
    "SUPABASE_KEY": "✅"
  },
  "config_source": "GitHub Secrets + Environment Variables"
}
```

## 🐛 **Troubleshooting**

### **Common Test Failures**

#### **"Missing configuration" Error**
```
❌ Missing configuration: ['SUPABASE_URL', 'SUPABASE_KEY']
```
**Solution:** Check that secret names in GitHub match exactly (case-sensitive)

#### **"Invalid Supabase key" Error**
```
❌ Database initialization failed: Invalid JWT
```
**Solution:** Use the anon/public key from Supabase, not the service_role key

#### **"B2 upload failed" Error**
```
❌ B2 upload failed (403): Invalid credentials
```
**Solutions:**
- Verify B2 application key ID and key are correct
- Check that bucket name exists and is accessible
- Ensure endpoint URL matches your bucket's region

#### **"Redis connection failed" Error**
```
❌ Redis connection failed: Connection refused
```
**Solutions:**
- Install Redis: `sudo apt install redis-server` (Ubuntu) or `brew install redis` (macOS)
- Start Redis: `sudo systemctl start redis-server` or `brew services start redis`
- Check Redis is running: `redis-cli ping` should return `PONG`

#### **"yt-dlp not found" Error**
```
❌ yt-dlp - run: pip install yt-dlp
```
**Solution:** Install yt-dlp: `pip install yt-dlp`

#### **"FFmpeg not found" Error**
```
❌ FFmpeg not found - please install FFmpeg
```
**Solutions:**
- Ubuntu/Debian: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`  
- Windows: Download from https://ffmpeg.org/download.html

### **Testing in Different Environments**

#### **Local Development**
- Use `.env` file for secrets
- Run `python test_setup.py` to verify everything works
- Use `python simple_demo.py` for quick metadata testing

#### **GitHub Actions**
- Secrets automatically available as environment variables
- Test workflow runs on every push/PR
- Check workflow logs for detailed error messages

#### **Docker**
- Environment variables passed through docker-compose
- Use `docker-compose up` to test full stack
- Check container logs: `docker-compose logs web`

#### **Cloud Deployment**
- Set environment variables in platform dashboard
- Use platform-specific health checks
- Monitor application logs for configuration issues

## 📊 **Test Coverage**

Our testing approach covers:

- ✅ **Configuration**: GitHub secrets, environment variables, validation
- ✅ **Dependencies**: Python packages, system tools (FFmpeg, Redis)
- ✅ **External Services**: Supabase database, Backblaze B2 storage
- ✅ **Core Functionality**: YouTube URL parsing, metadata extraction
- ✅ **Integration**: Full application stack, API endpoints
- ✅ **Deployment**: Docker, CI/CD workflows, cloud platforms

## 🚀 **Continuous Testing**

### **Automated Testing**
- Test workflow runs on every push to main branch
- Validates all components work together
- Catches configuration issues early

### **Manual Testing**
- Use verification script before major deployments
- Test new YouTube URL types with simple demo
- Monitor health endpoints in production

### **Monitoring**
- Set up alerts for health check failures
- Monitor queue status for performance issues  
- Track error logs for recurring problems

This comprehensive testing approach ensures your YouTube video scraper works reliably across all environments and configurations!