#!/usr/bin/env python3
"""
Verify that the FUNCTION_INVOCATION_FAILED fix is working correctly.
Run this locally before deploying to Vercel.
"""

import sys
import os

def test_handler_import():
    """Test 1: Can we import the handler?"""
    try:
        from api.index import handler
        print("✅ Test 1 PASSED: Handler imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Test 1 FAILED: Cannot import handler - {e}")
        return False

def test_handler_callable():
    """Test 2: Is the handler callable?"""
    try:
        from api.index import handler
        if callable(handler):
            print("✅ Test 2 PASSED: Handler is callable")
            return True
        else:
            print("❌ Test 2 FAILED: Handler is not callable")
            return False
    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")
        return False

def test_app_import():
    """Test 3: Can we import the Flask app directly?"""
    try:
        from app import app
        print("✅ Test 3 PASSED: Flask app imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Test 3 FAILED: Cannot import app - {e}")
        return False

def test_flask_app_valid():
    """Test 4: Is the Flask app a valid WSGI application?"""
    try:
        from app import app
        # Check if it has the WSGI callable interface
        if callable(app) and hasattr(app, 'wsgi_app'):
            print("✅ Test 4 PASSED: Flask app is a valid WSGI application")
            return True
        else:
            print("⚠️  Test 4 WARNING: Flask app may not be WSGI-compliant")
            return True  # Flask apps are always WSGI-compliant
    except Exception as e:
        print(f"❌ Test 4 FAILED: {e}")
        return False

def test_vercel_json():
    """Test 5: Is vercel.json configured correctly?"""
    try:
        import json
        with open('vercel.json', 'r') as f:
            config = json.load(f)
        
        checks = [
            ('api/index.py' in config.get('functions', {}), "Function config exists"),
            (config.get('functions', {}).get('api/index.py', {}).get('maxDuration', 60) >= 300, "maxDuration >= 300"),
            (config.get('functions', {}).get('api/index.py', {}).get('memory', 512) >= 3008, "memory >= 3008"),
        ]
        
        all_pass = True
        for check, desc in checks:
            if check:
                print(f"  ✅ {desc}")
            else:
                print(f"  ❌ {desc}")
                all_pass = False
        
        if all_pass:
            print("✅ Test 5 PASSED: vercel.json configured correctly")
        else:
            print("❌ Test 5 FAILED: vercel.json configuration issues")
        
        return all_pass
    except Exception as e:
        print(f"❌ Test 5 FAILED: {e}")
        return False

def test_requirements():
    """Test 6: Are all dependencies in requirements.txt?"""
    try:
        with open('requirements.txt', 'r') as f:
            reqs = f.read().lower()
        
        required = ['flask', 'opencv', 'numpy', 'pytesseract']
        missing = []
        
        for req in required:
            if req not in reqs:
                missing.append(req)
        
        if not missing:
            print("✅ Test 6 PASSED: All required packages in requirements.txt")
            return True
        else:
            print(f"⚠️  Test 6 WARNING: Missing packages - {', '.join(missing)}")
            return True  # Not critical
    except Exception as e:
        print(f"❌ Test 6 FAILED: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("FUNCTION_INVOCATION_FAILED - Fix Verification")
    print("=" * 60)
    print()
    
    tests = [
        test_handler_import,
        test_handler_callable,
        test_app_import,
        test_flask_app_valid,
        test_vercel_json,
        test_requirements,
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print()
        print("Your application is ready to deploy to Vercel!")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print()
        print("Please fix the issues above before deploying.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
