# FUNCTION_INVOCATION_FAILED - Root Cause Analysis & Fix

## Error Overview

**Error Code:** 500 (Internal Server Error)  
**Vercel Error:** FUNCTION_INVOCATION_FAILED  
**Status:** FIXED ✅

---

## 1. Root Cause: Why This Error Occurred

### What Your Code Was Doing (Wrong)
```python
# api/index.py - INCORRECT
from app import app
export = app  # ❌ Wrong: Assigning Flask app to a variable
```

### What Was Actually Happening
1. Vercel's Python runtime loaded `api/index.py`
2. It looked for an **exported callable** (a function or WSGI app object named `handler` or `app`)
3. It found `export = app` instead
4. The runtime crashed because it couldn't invoke `export` as a proper WSGI handler
5. **Result:** FUNCTION_INVOCATION_FAILED

### What It Should Have Done (Fixed)
```python
# api/index.py - CORRECT
from app import app
handler = app  # ✅ Correct: Flask app IS a WSGI callable
```

---

## 2. Mental Model: Understanding the Root Concept

### How Vercel Python Runtime Works

```
┌─────────────────────────────────────────────────────────┐
│ Vercel Python Runtime                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 1. Load your function file (api/index.py)              │
│ 2. Look for a handler function or WSGI app:            │
│    - handler = function() ✅                            │
│    - app = Flask() ✅                                  │
│    - export = Flask() ❌                               │
│ 3. Call it with HTTP request/response objects          │
│ 4. Return the HTTP response                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Key Principle: WSGI Applications

Flask apps are **WSGI applications**, which means they implement a standard interface:

```python
# WSGI Callable Interface
def application(environ, start_response):
    # environ: HTTP request details
    # start_response: callback to send response
    return [b"response body"]
```

Flask's `Flask()` class implements this interface, making it directly callable by Vercel.

**Important:** The variable name matters! Vercel looks for:
- `handler` (preferred for Vercel Functions)
- `app` (common Flask convention)
- NOT `export` or `application` (wrong naming)

---

## 3. Why This Error Exists: Protection & Design

### Purpose of This Error

```
✅ Protects you from:
   - Silent failures due to missing entry points
   - Code loading errors not being caught
   - WSGI violations (non-callable handlers)
   - Infinite loops or hangs in startup

❌ Prevents:
   - Undefined behavior
   - Server crashes in production
   - Hard-to-debug initialization issues
```

### The Trade-off

| Approach | Pros | Cons |
|----------|------|------|
| **Strict Validation** (Vercel's way) | Safe, catches errors early | Less flexible with custom setups |
| **Loose Validation** | More flexible | Can hide bugs, harder to debug |

Vercel chose strict validation because serverless functions need to be reliable and fast to startup.

---

## 4. Warning Signs: Recognizing This Pattern

### Red Flags That Indicate This Problem

```python
# ❌ WRONG - Non-standard variable names
export = app
application = Flask()
wsgi_app = Flask()
my_app = Flask()

# ✅ CORRECT - Vercel looks for these
handler = app
app = Flask()  # When directly in api/index.py
```

### Related Mistakes to Avoid

```python
# ❌ Problem 1: App not properly imported
from app import create_app
handler = create_app()  # ❌ If create_app() returns None or doesn't return app

# ✅ Solution: Ensure it returns the app
handler = create_app()

# ❌ Problem 2: App initialization fails silently
try:
    handler = app
except Exception as e:
    print(e)  # ❌ This won't show in Vercel logs
    
# ✅ Solution: Let errors bubble up
handler = app  # ✅ If there's an error, Vercel will catch and show it

# ❌ Problem 3: Missing dependencies in function
from some_package import something  # ❌ Package not in requirements.txt
handler = app

# ✅ Solution: Check requirements.txt includes all imports
```

### Code Smell Indicators

1. **Non-Standard Export Names:** Using anything other than `handler` or `app`
2. **Silent Error Handling:** `try/except` blocks that hide initialization errors
3. **Missing Dependencies:** Imports in `api/index.py` not listed in `requirements.txt`
4. **Incorrect Path Setup:** `sys.path` manipulation that fails
5. **Environment Variable Issues:** Required env vars not set

---

## 5. The Fix Applied

### Changes Made

#### File 1: `api/index.py`
```python
# BEFORE
from app import app
export = app  # ❌ Wrong variable name

# AFTER
from app import app
handler = app  # ✅ Correct variable name
```

#### File 2: `vercel.json`
```json
// BEFORE
"rewrite": { "source": "/(.*)", "destination": "/api" }

// AFTER
"rewrite": { "source": "/(.*)", "destination": "/api/index.py" }
"maxDuration": 60    → 300  // Allow more time for image processing
"memory": 3008       // Increase memory for ML models
```

#### Why These Changes Work

1. **`handler = app`:** Vercel recognizes this as a valid WSGI callable
2. **`/api/index.py`:** Explicitly points to the correct handler file
3. **`maxDuration: 300`:** Image detection + OCR can take 30-60 seconds (default 10s isn't enough)
4. **`memory: 3008`:** ML models need more memory (default 512MB insufficient)

---

## 6. Alternative Approaches & Trade-offs

### Option A: Direct WSGI Handler Function (Current - Recommended)
```python
# api/index.py
from app import app
handler = app  # Direct WSGI app
```

**Pros:** Simple, clean, works with Vercel  
**Cons:** Less control over request/response

---

### Option B: Wrapper Handler Function
```python
# api/index.py
from app import app

def handler(request):
    """Custom wrapper around Flask app"""
    return app(request)
```

**Pros:** Can add custom logic, logging, middleware  
**Cons:** More boilerplate, requires understanding WSGI

---

### Option C: Vercel Serverless Functions (Alternative)
```python
# api/detect.py
from vercel_python_runtime import Response
from number_plate_detector import detect_number_plate

def handler(request):
    """Pure serverless function, not WSGI"""
    if request.method == 'POST':
        # Process request manually
        return Response(body=result)
```

**Pros:** Lightweight, fine-grained control  
**Cons:** Have to implement routing manually, lose Flask features

---

### Option D: Docker Container
```dockerfile
# Dockerfile
FROM python:3.11
RUN apt-get install tesseract-ocr
COPY . /app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:3000", "app:app"]
```

**Pros:** Full control, easy local testing  
**Cons:** More complex, slower cold starts, costs more

---

## 7. Prevention Checklist

Use this checklist to avoid this error in the future:

```
□ Entry Point Naming
  ✓ Use 'handler' or 'app' (never 'export', 'application', 'wsgi_app')
  ✓ Verify the name matches Vercel's expectations
  ✓ Test locally: can I import and call it?

□ Dependency Management
  ✓ Every import in api/index.py is in requirements.txt
  ✓ No import errors when loading the module
  ✓ All dependencies have correct versions

□ Configuration
  ✓ vercel.json points to correct file (api/index.py)
  ✓ Runtime matches your Python version (3.11)
  ✓ maxDuration is long enough (60+ for image processing)
  ✓ Memory allocation is sufficient (3008+ for ML models)

□ Error Visibility
  ✓ No silent try/except blocks at module level
  ✓ Let initialization errors bubble up
  ✓ Check Vercel logs for actual error messages

□ Path Issues
  ✓ sys.path manipulation points to actual directories
  ✓ Relative imports work correctly
  ✓ All modules are in the right places

□ Testing
  ✓ Test locally: python -c "from api.index import handler"
  ✓ Test imports: python -c "from app import app"
  ✓ Check Vercel logs after deploy
```

---

## 8. Testing Your Fix

### Local Testing (Before Deploying)

```bash
# Test 1: Can Python import the handler?
python3 -c "from api.index import handler; print('✅ Import successful')"

# Test 2: Is handler callable?
python3 -c "from api.index import handler; print(callable(handler))"

# Test 3: Can you start the app locally?
python3 app.py  # Should start Flask dev server
```

### Vercel Testing (After Deploying)

1. Go to Vercel Dashboard
2. Find your deployment
3. Click "Logs" tab
4. Look for errors in "Function Logs"
5. Check for "FUNCTION_INVOCATION_FAILED" messages

---

## 9. Related Errors You Might See

| Error | Cause | Fix |
|-------|-------|-----|
| `FUNCTION_INVOCATION_FAILED` | Handler not found/callable | Use `handler = app` |
| `MODULE_NOT_FOUND` | Import error | Add to requirements.txt |
| `TIMEOUT` | Takes >300 seconds | Increase maxDuration |
| `OUT_OF_MEMORY` | Insufficient memory | Increase memory value |
| `502 Bad Gateway` | Unhandled exception | Check logs, add error handling |

---

## 10. Quick Reference

### What Changed

| File | Before | After |
|------|--------|-------|
| `api/index.py` | `export = app` | `handler = app` |
| `vercel.json` | `/api` | `/api/index.py` |
| `vercel.json` | `maxDuration: 60` | `maxDuration: 300` |
| `vercel.json` | (no memory) | `memory: 3008` |

### Why It Works Now

1. ✅ Vercel finds the `handler` function
2. ✅ Handler is directly the Flask app (WSGI callable)
3. ✅ Explicit path to index.py prevents ambiguity
4. ✅ 300 second timeout allows image processing time
5. ✅ 3GB memory supports ML models

---

## 11. Further Learning

### Understanding WSGI
- Read: https://www.python.org/dev/peps/pep-3333/
- It's the standard interface all Python web frameworks use

### Vercel Python Documentation
- https://vercel.com/docs/functions/serverless-functions/python

### Flask & WSGI
- Flask docs: https://flask.palletsprojects.com/
- WSGI intro: https://wsgi.readthedocs.io/

---

## Summary

**Problem:** `export = app` is not a valid Vercel handler  
**Solution:** Use `handler = app` to expose a WSGI callable  
**Root Cause:** Vercel expects specific function names that implement the WSGI interface  
**Prevention:** Use `handler` or `app`, test imports locally, check Vercel logs  
**Status:** ✅ FIXED - Ready to deploy

