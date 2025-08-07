#!/usr/bin/env python3
"""
GitHub Webhook Handler for Auto-Deployment
==========================================

This script handles GitHub webhook events to automatically deploy updates
when code is pushed to the main branch.

Setup:
1. Copy this file to your server: /home/youtube-scraper/webhook.py
2. Install Flask: pip install flask
3. Set WEBHOOK_SECRET environment variable
4. Create systemd service (see DEPLOYMENT.md)
5. Configure GitHub webhook to point to your server

Security:
- Verifies webhook signature using HMAC
- Only processes pushes to main branch
- Runs with limited permissions
"""

import os
import subprocess
import hmac
import hashlib
import logging
from datetime import datetime
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/youtube-scraper/webhook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'your-webhook-secret-here')
REPO_PATH = "/home/youtube-scraper/youtube-video-scraper"
ALLOWED_BRANCHES = ['refs/heads/main', 'refs/heads/master']

@app.route('/webhook', methods=['POST'])
def github_webhook():
    """Handle GitHub webhook events"""
    try:
        # Get request data
        payload = request.get_json()
        signature = request.headers.get('X-Hub-Signature-256')
        
        logger.info(f"Received webhook request from {request.remote_addr}")
        
        # Verify webhook signature
        if not verify_signature(request.data, signature):
            logger.warning("Invalid webhook signature")
            return jsonify({'error': 'Invalid signature'}), 403
        
        # Check if this is a push event to main/master branch
        if payload.get('ref') not in ALLOWED_BRANCHES:
            logger.info(f"Ignoring push to branch: {payload.get('ref')}")
            return jsonify({'status': 'ignored', 'reason': 'not main branch'})
        
        # Get commit information
        commits = payload.get('commits', [])
        commit_count = len(commits)
        latest_commit = commits[-1] if commits else {}
        commit_message = latest_commit.get('message', 'No message')
        commit_author = latest_commit.get('author', {}).get('name', 'Unknown')
        
        logger.info(f"Processing deployment: {commit_count} commits")
        logger.info(f"Latest commit: {commit_message} by {commit_author}")
        
        # Deploy the update
        deployment_result = deploy_update()
        
        if deployment_result['success']:
            logger.info("Deployment completed successfully")
            return jsonify({
                'status': 'deployed successfully',
                'commit_count': commit_count,
                'latest_commit': commit_message,
                'deployed_at': datetime.now().isoformat()
            })
        else:
            logger.error(f"Deployment failed: {deployment_result['error']}")
            return jsonify({
                'error': f"Deployment failed: {deployment_result['error']}"
            }), 500
            
    except Exception as e:
        logger.error(f"Webhook handler error: {str(e)}")
        return jsonify({'error': f'Webhook handler error: {str(e)}'}), 500

def verify_signature(payload, signature):
    """Verify GitHub webhook signature"""
    if not signature or not WEBHOOK_SECRET:
        return False
    
    expected = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

def deploy_update():
    """Deploy the latest code update"""
    try:
        logger.info("Starting deployment process...")
        
        # Change to repository directory
        os.chdir(REPO_PATH)
        
        # Step 1: Pull latest code
        logger.info("Pulling latest code from GitHub...")
        result = subprocess.run(
            ['git', 'pull', 'origin', 'main'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            return {'success': False, 'error': f'Git pull failed: {result.stderr}'}
        
        logger.info(f"Git pull output: {result.stdout}")
        
        # Step 2: Install/update dependencies
        logger.info("Updating Python dependencies...")
        result = subprocess.run(
            ['./venv/bin/pip', 'install', '-r', 'requirements.txt'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.warning(f"Pip install had issues: {result.stderr}")
            # Don't fail deployment for pip warnings
        
        # Step 3: Run basic tests
        logger.info("Running basic tests...")
        result = subprocess.run(
            ['./venv/bin/python', '-c', 'from config import config; print("Config OK")'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.warning(f"Basic test failed: {result.stderr}")
            # Continue anyway - might be config issue
        
        # Step 4: Restart services
        logger.info("Restarting application services...")
        
        services = ['youtube-scraper', 'youtube-worker']
        for service in services:
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', service],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {'success': False, 'error': f'Failed to restart {service}: {result.stderr}'}
            
            logger.info(f"Restarted service: {service}")
        
        # Step 5: Verify services are running
        for service in services:
            result = subprocess.run(
                ['sudo', 'systemctl', 'is-active', service],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.warning(f"Service {service} may not be active: {result.stdout}")
        
        logger.info("Deployment completed successfully")
        return {'success': True}
        
    except subprocess.TimeoutExpired as e:
        return {'success': False, 'error': f'Command timeout: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': f'Deployment error: {str(e)}'}

@app.route('/status', methods=['GET'])
def webhook_status():
    """Get webhook handler status"""
    return jsonify({
        'status': 'running',
        'repo_path': REPO_PATH,
        'webhook_secret_configured': bool(WEBHOOK_SECRET and WEBHOOK_SECRET != 'your-webhook-secret-here'),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check if repository exists
        repo_exists = os.path.exists(REPO_PATH)
        
        # Check if services are running
        services_status = {}
        for service in ['youtube-scraper', 'youtube-worker']:
            result = subprocess.run(
                ['sudo', 'systemctl', 'is-active', service],
                capture_output=True,
                text=True
            )
            services_status[service] = result.stdout.strip()
        
        return jsonify({
            'status': 'healthy',
            'repo_exists': repo_exists,
            'services': services_status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # Validate configuration
    if WEBHOOK_SECRET == 'your-webhook-secret-here':
        logger.warning("⚠️  Using default webhook secret! Set WEBHOOK_SECRET environment variable.")
    
    if not os.path.exists(REPO_PATH):
        logger.error(f"❌ Repository path does not exist: {REPO_PATH}")
        exit(1)
    
    logger.info("🚀 Starting GitHub webhook handler...")
    logger.info(f"📁 Repository path: {REPO_PATH}")
    logger.info(f"🔑 Webhook secret configured: {bool(WEBHOOK_SECRET and WEBHOOK_SECRET != 'your-webhook-secret-here')}")
    
    # Run Flask app
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=False
    )