# Quick Reference: FUNCTION_INVOCATION_FAILED Fix

## The Problem
App returns 500 error: `FUNCTION_INVOCATION_FAILED`

## The Cause
Wrong variable name in `api/index.py`:
```python
export = app  # ❌ Vercel doesn't recognize this
```

## The Solution
Change to:
```python
handler = app  # ✅ Vercel recognizes this
```

## Files Changed
1. `api/index.py` - Changed `export = app` to `handler = app`
2. `vercel.json` - Updated configuration (timeout, memory, destination)

## How to Verify
```bash
python3 verify_fix.py
```

Should show all 6 tests passing.

## How to Deploy
```bash
git add .
git commit -m "Fix FUNCTION_INVOCATION_FAILED"
git push origin main
```

## Expected Result
- App loads without 500 error
- Homepage displays correctly
- Image upload works
- Detection processes successfully

## Why It Works
Vercel's Python runtime looks for a handler named `handler`. Flask apps are WSGI callables, so they work perfectly as handlers.

## Prevention Tips
- Always use `handler` as the variable name for Vercel
- Test locally: `python3 -c "from api.index import handler"`
- Check requirements.txt has all imports
- Set appropriate maxDuration and memory in vercel.json

## Key Concepts
- **WSGI:** Standard Python web application interface
- **Handler:** Entry point that Vercel calls for each request
- **Naming:** Vercel expects specific names (`handler`, `app`)

## Learn More
See these files for detailed explanations:
- `FUNCTION_INVOCATION_FAILED_ANALYSIS.md` - Full technical analysis
- `BEFORE_AFTER_COMPARISON.md` - Visual before/after
- `FIX_SUMMARY.md` - Detailed summary
