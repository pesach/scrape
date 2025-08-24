#!/usr/bin/env python3
# Test Supabase connection
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from config import config
    from supabase import create_client
    
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        logger.error('Missing Supabase configuration')
        sys.exit(1)
    
    logger.info('Testing Supabase connection...')
    client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    
    result = client.table('videos').select('id').limit(1).execute()
    logger.info(f'Success! Found {len(result.data) if result.data else 0} records')
    
    print('✅ Supabase connection successful!')
    
except Exception as e:
    logger.error(f'Test failed: {e}')
    sys.exit(1)
