# 🔧 Setting Up Your Credentials

You need to replace the placeholder values in your `.env` file with real credentials. Here's how to get each one:

## 📊 **1. Supabase Configuration**

### Get Your Supabase URL and Key:

1. **Go to [Supabase Dashboard](https://app.supabase.com/)**
2. **Select your project** (or create one if you haven't)
3. **Go to Settings → API**
4. **Copy these values:**
   - `Project URL` → Use for `SUPABASE_URL`
   - `anon public` key → Use for `SUPABASE_KEY` (NOT the secret key!)

### Example:
```bash
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTY0MzY3OTIwMCwiZXhwIjoxOTU5MjU1MjAwfQ.example-key
```

## ☁️ **2. Backblaze B2 Configuration**

### Get Your B2 Credentials:

1. **Go to [Backblaze B2 Console](https://secure.backblaze.com/b2_buckets.htm)**
2. **Create an Application Key:**
   - Go to "App Keys" → "Add a New Application Key"
   - Give it a name like "YouTube Scraper"
   - **Copy the Key ID and Application Key** (save them immediately!)
3. **Create a Bucket:**
   - Go to "Buckets" → "Create a Bucket"
   - Choose a unique name
   - Set to "Private" for security
4. **Find your endpoint URL:**
   - Usually `https://s3.us-west-004.backblazeb2.com` (check your region)

### Example:
```bash
B2_APPLICATION_KEY_ID=004a1b2c3d4e5f6789abcdef
B2_APPLICATION_KEY=K004abcdefghijklmnopqrstuvwxyz123456789
B2_BUCKET_NAME=my-youtube-videos-bucket
B2_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
```

## ⚡ **3. Redis Configuration**

Redis is already running! The default configuration should work:

```bash
REDIS_URL=redis://localhost:6379/0
```

---

## 🧑‍💻 **Optional: Human-like Scraping Settings**

These help the scraper behave like a real browser session and a human viewer.

```bash
# Realistic browser headers
SCRAPER_USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
SCRAPER_ACCEPT_LANGUAGE="en-US,en;q=0.9"

# Cookies: either provide a cookies.txt or extract from a browser profile
YT_COOKIES_FILE=/path/to/cookies.txt
COOKIES_FROM_BROWSER=chrome  # chrome|firefox|brave|edge

# Watch-time pacing
SIMULATE_WATCH_TIME=true
WATCH_SPEED=1.25
HUMAN_DELAY_MIN_SEC=3.0
HUMAN_DELAY_MAX_SEC=10.0

# Optional hard cap (bytes/sec). If set, overrides watch-time rate
DOWNLOAD_RATELIMIT_BPS=0
```

Notes:
- If both `YT_COOKIES_FILE` and `COOKIES_FROM_BROWSER` are set, `YT_COOKIES_FILE` wins.
- When watch-time simulation is enabled, downloads are rate-limited to approximate playback.

---

## 🚀 **Quick Setup Commands**

### 1. Edit your .env file:
```bash
nano .env
```

### 2. Replace the placeholder values with your real credentials

### 3. Test your setup:
```bash
python3 debug_env.py
python3 test_setup.py
```

### 4. Start the services:
```bash
# Terminal 1 - Start the web server
python3 run.py

# Terminal 2 - Start the worker (includes scheduler for daily updates)
python3 start_worker.py
```

---

## ⚠️ **Security Notes**

- ✅ **Use the `anon public` key from Supabase** (not the secret key)
- ✅ **Keep your .env file private** (it's already in .gitignore)
- ✅ **Set your B2 bucket to Private**
- ✅ **Never commit real credentials to git**

---

## 🔍 **Troubleshooting**

### "Invalid API Key" Errors:

1. **Double-check your Supabase key** - make sure it's the `anon public` key
2. **Verify your Supabase URL** - should end with `.supabase.co`
3. **Test your B2 credentials** - try logging into B2 console
4. **Check for extra spaces** - credentials should have no spaces

### Test Individual Components:
```bash
# Test just the database
python3 -c "from database import Database; db = Database(); print('✅ Database OK')"

# Test just B2 storage
python3 -c "from storage import BackblazeB2Storage; storage = BackblazeB2Storage(); print('✅ Storage OK')"
```

### Still Having Issues?
Run the comprehensive diagnostic:
```bash
python3 debug_env.py
```

This will show you exactly what's missing or misconfigured!