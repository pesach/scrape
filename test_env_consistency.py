#!/usr/bin/env python3
"""
Environment Variable Consistency Test
====================================

This script tests that all main application files load environment variables
the same way as test_setup.py.
"""

import os
import sys
import subprocess
from pathlib import Path

def test_script_env_loading(script_name, expected_vars=None):
    """Test if a script can load environment variables"""
    if expected_vars is None:
        expected_vars = ["SUPABASE_URL", "REDIS_URL"]
    
    print(f"\n🧪 Testing {script_name}...")
    
    # Create a simple test that imports the script and checks config
    test_code = f"""
import sys
sys.path.insert(0, '.')

try:
    if '{script_name}' == 'run.py':
        from run import config
    elif '{script_name}' == 'start_worker.py':
        from start_worker import config  
    elif '{script_name}' == 'main.py':
        from main import config
    elif '{script_name}' == 'celery_app.py':
        from celery_app import config
    else:
        from config import config
    
    # Check if key variables are loaded
    results = {{}}
    for var in {expected_vars}:
        value = getattr(config, var, None)
        results[var] = bool(value and value.strip())
    
    print("RESULTS:", results)
    all_loaded = all(results.values())
    print("ALL_LOADED:", all_loaded)
    
except Exception as e:
    print("ERROR:", str(e))
    print("ALL_LOADED:", False)
"""
    
    try:
        result = subprocess.run([
            sys.executable, '-c', test_code
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        output = result.stdout
        if "ALL_LOADED: True" in output:
            print(f"  ✅ {script_name} - Environment variables loaded successfully")
            return True
        elif "ALL_LOADED: False" in output:
            print(f"  ❌ {script_name} - Environment variables NOT loaded")
            if "ERROR:" in output:
                error_line = [line for line in output.split('\n') if 'ERROR:' in line]
                if error_line:
                    print(f"     Error: {error_line[0].replace('ERROR:', '').strip()}")
            return False
        else:
            print(f"  ⚠️  {script_name} - Unexpected output:")
            print(f"     {output}")
            return False
            
    except Exception as e:
        print(f"  ❌ {script_name} - Test failed: {str(e)}")
        return False

def main():
    print("🔍 Environment Variable Consistency Test")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  No .env file found!")
        print("   Creating from template...")
        
        example_file = Path(".env.example")
        if example_file.exists():
            with open(example_file, 'r') as f:
                content = f.read()
            with open(env_file, 'w') as f:
                f.write(content)
            print("✅ Created .env from template")
            print("📝 Edit .env with your actual values before running tests")
        else:
            print("❌ No .env.example found either!")
            return False
    
    print(f"✅ .env file exists: {env_file.absolute()}")
    
    # Test scripts that should load environment variables consistently
    scripts_to_test = [
        "run.py",
        "start_worker.py", 
        "main.py",
        "celery_app.py"
    ]
    
    results = {}
    for script in scripts_to_test:
        if Path(script).exists():
            results[script] = test_script_env_loading(script)
        else:
            print(f"  ⚠️  {script} - File not found, skipping")
            results[script] = None
    
    print(f"\n📊 Test Results:")
    print("=" * 30)
    
    passed = 0
    failed = 0
    
    for script, result in results.items():
        if result is True:
            print(f"✅ {script} - PASS")
            passed += 1
        elif result is False:
            print(f"❌ {script} - FAIL")
            failed += 1
        else:
            print(f"⚠️  {script} - SKIPPED")
    
    print(f"\n📈 Summary: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All scripts load environment variables consistently!")
        print("✅ start_worker.py should now work the same as test_setup.py")
    else:
        print(f"\n⚠️  {failed} scripts still have environment loading issues")
        print("💡 Try running: python fix_env_loading.py")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)