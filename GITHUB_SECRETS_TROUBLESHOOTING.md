# 🔐 GitHub Secrets Troubleshooting Guide

This guide helps resolve issues with accessing GitHub Repository Secrets.

## 🚨 **Common Issue: "Cannot Access GitHub Secrets"**

If your application can't access GitHub Repository Secrets, here are the most likely causes and solutions:

## 📋 **Requirements for GitHub Secrets Access**

### **✅ Repository Requirements:**
- **Public OR Private**: Both work, but private repos need proper permissions
- **Secrets Location**: Must be in **Repository Secrets**, not Environment Secrets
- **Secret Names**: Must match exactly (case-sensitive)

### **✅ Access Context Requirements:**
- **GitHub Actions**: Secrets automatically available as environment variables
- **Local Development**: Secrets NOT available (use `.env` file instead)
- **Server Deployment**: Secrets NOT directly available (need manual setup)

## 🔍 **Where GitHub Secrets Work vs Don't Work**

| Context | GitHub Secrets Available? | Alternative |
|---------|---------------------------|-------------|
| **GitHub Actions Workflows** | ✅ YES (automatic) | N/A |
| **Local Development** | ❌ NO | Use `.env` file |
| **Server Deployment** | ❌ NO | Manual environment setup |
| **Docker on Server** | ❌ NO | Pass via environment variables |
| **Codespaces** | ✅ YES (if configured) | N/A |

## 🛠️ **Solutions by Context**

### **1. GitHub Actions (Should Work Automatically)**

**If secrets aren't working in GitHub Actions:**

1. **Check Secret Names** (case-sensitive):
   ```yaml
   # In .github/workflows/test-secrets.yml
   env:
     SUPABASE_URL: ${{ secrets.SUPABASE_URL }}      # Must match exactly
     SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}      # Case matters!
   ```

2. **Verify Secrets Exist**:
   - Go to: **Repository → Settings → Secrets and variables → Actions**
   - Confirm all 6 secrets are listed:
     - `SUPABASE_URL`
     - `SUPABASE_KEY` 
     - `B2_APPLICATION_KEY_ID`
     - `B2_APPLICATION_KEY`
     - `B2_BUCKET_NAME`
     - `B2_ENDPOINT_URL`

3. **Check Repository Type**:
   - **Private repos**: Ensure GitHub Actions are enabled
   - **Forked repos**: Secrets from original repo are NOT inherited

### **2. Local Development (Expected Behavior)**

**GitHub Secrets are NOT available locally. This is normal!**

**Solution: Use `.env` file**
```bash
# Create .env file in project root
cp .env.example .env
nano .env

# Add your actual values:
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
# ... etc
```

### **3. Server Deployment (Manual Setup Required)**

**GitHub Secrets are NOT automatically available on servers.**

**Solution A: Manual Environment Setup**
```bash
# On your server, edit environment file
sudo nano /etc/environment

# Add your secrets:
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
B2_APPLICATION_KEY_ID=your_b2_key_id
B2_APPLICATION_KEY=your_b2_application_key
B2_BUCKET_NAME=your-bucket-name
B2_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
```

**Solution B: Use GitHub CLI (if server has access)**
```bash
# Install GitHub CLI on server
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# Authenticate
gh auth login

# Fetch secrets (requires repo access)
gh secret list --repo yourusername/reponame
```

**Solution C: Docker with Environment Variables**
```bash
# Pass secrets to Docker
docker run -e SUPABASE_URL="$SUPABASE_URL" -e SUPABASE_KEY="$SUPABASE_KEY" your-app
```

## 🔐 **SSH Key Access (For Private Repos)**

**SSH keys are needed for:**
- ✅ Cloning private repositories
- ✅ Pulling updates via `git pull`
- ❌ NOT needed for accessing GitHub Secrets

**If you need SSH access for private repo:**

1. **Generate SSH key on server:**
   ```bash
   ssh-keygen -t ed25519 -C "your-email@example.com"
   ```

2. **Add public key to GitHub:**
   ```bash
   cat ~/.ssh/id_ed25519.pub
   # Copy output and add to GitHub → Settings → SSH Keys
   ```

3. **Test SSH access:**
   ```bash
   ssh -T git@github.com
   ```

4. **Clone using SSH:**
   ```bash
   git clone git@github.com:pesach/scrape.git
   ```

## 🧪 **Testing GitHub Secrets Access**

### **Test in GitHub Actions**
Run the "Test GitHub Secrets Configuration" workflow:
1. Go to **Repository → Actions**
2. Find **"Test GitHub Secrets Configuration"**
3. Click **"Run workflow"**
4. Check results

### **Test Locally (Should Fail)**
```bash
python -c "import os; print('SUPABASE_URL:', os.getenv('SUPABASE_URL'))"
# Expected: None (secrets not available locally)
```

### **Test on Server**
```bash
# After setting up environment variables
python -c "from config import config; print('Config loaded:', bool(config.SUPABASE_URL))"
```

## 🚨 **Common Mistakes**

1. **❌ Expecting secrets to work locally**
   - **Fix**: Use `.env` file for local development

2. **❌ Expecting secrets to work on server automatically**
   - **Fix**: Manually set environment variables on server

3. **❌ Using Environment Secrets instead of Repository Secrets**
   - **Fix**: Ensure secrets are in Repository → Settings → Secrets → Actions

4. **❌ Case-sensitive secret names**
   - **Fix**: Check exact spelling: `SUPABASE_URL` not `supabase_url`

5. **❌ Forked repo expecting original secrets**
   - **Fix**: Add secrets to your forked repository

6. **❌ Private repo without proper permissions**
   - **Fix**: Ensure GitHub Actions are enabled for private repos

## 📋 **Debugging Checklist**

- [ ] **Repository Secrets exist** (not Environment Secrets)
- [ ] **Secret names match exactly** (case-sensitive)
- [ ] **Testing in correct context** (GitHub Actions vs local vs server)
- [ ] **Private repo has Actions enabled**
- [ ] **Not expecting secrets in local development**
- [ ] **Server environment variables set manually**
- [ ] **SSH keys configured** (if using private repo)

## 🎯 **Quick Fix Commands**

**For Local Development:**
```bash
cp .env.example .env
nano .env  # Add your actual values
```

**For Server Deployment:**
```bash
sudo nano /etc/environment  # Add secrets here
source /etc/environment      # Reload environment
```

**For GitHub Actions:**
```bash
# Check workflow logs for specific error messages
# Secrets should work automatically if properly configured
```

## 💡 **Key Takeaway**

**GitHub Repository Secrets are ONLY available in GitHub Actions workflows, not in local development or server deployments.** For those contexts, you need to manually set environment variables or use `.env` files.

This is by design for security reasons! 🔒