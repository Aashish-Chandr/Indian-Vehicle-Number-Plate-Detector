# Troubleshooting Guide

## Common Issues and Solutions

### 1. FUNCTION_INVOCATION_FAILED
**Symptoms**: 500 error when accessing the app
**Cause**: Handler not properly exported or import errors
**Solution**:
- Verify `api/index.py` has `handler = app`
- Check that all imports in app.py are correct
- Run `python3 -m py_compile app.py` to check syntax
- Check Vercel logs for specific error

### 2. Templates Not Found
**Symptoms**: "TemplateNotFound: index.html"
**Cause**: Templates folder not in correct location or not configured
**Solution**:
- Ensure `templates/` folder exists in project root
- Check Flask initialization: `Flask(__name__, template_folder='templates')`
- Verify file paths in render_template() calls

### 3. Static Files Not Serving
**Symptoms**: CSS/JS files return 404
**Cause**: Static folder misconfigured
**Solution**:
- Ensure `static/` folder exists
- Check Flask initialization: `Flask(__name__, static_folder='static')`
- Verify paths in HTML templates use `/static/` prefix

### 4. Build Fails - Tesseract Not Found
**Symptoms**: "tesseract is not installed"
**Cause**: Tesseract not installed during build
**Solution**:
- Verify build.sh installs tesseract-ocr
- Check Vercel build logs for installation errors
- May require additional apt packages

### 5. Memory Limit Exceeded
**Symptoms**: Function timeout or killed
**Cause**: Processing large images or model loading issues
**Solution**:
- Increase memory in vercel.json: `"memory": 3008`
- Optimize image processing
- Pre-load models at startup
- Compress images before processing

### 6. File Upload Size Limit
**Symptoms**: "413 Request Entity Too Large"
**Cause**: File exceeds 5MB limit
**Solution**:
- Check app.config['MAX_CONTENT_LENGTH'] in app.py
- User needs to upload smaller image
- This is by design to prevent resource exhaustion

### 7. OpenCV Import Fails
**Symptoms**: "ImportError: cannot open shared object file"
**Cause**: Missing system libraries
**Solution**:
- build.sh must install: libsm6, libxext6, libxrender-dev, libglib2.0-0
- These are essential for OpenCV functionality
- Check build script is being run

### 8. SESSION_SECRET Error in Production
**Symptoms**: Secret key warning in logs
**Cause**: SESSION_SECRET not set in Vercel environment
**Solution**:
- Go to Vercel dashboard → Settings → Environment Variables
- Add: `SESSION_SECRET=<your-secure-key>`
- Generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- Redeploy after setting

### 9. Image Detection Returns "No plate detected"
**Symptoms**: Even with number plate image, detection fails
**Cause**: Image quality or model issues
**Solution**:
- Ensure image has clear number plate
- Try preprocessing: resize, enhance contrast
- Check cascade files are downloaded
- Verify model weights are correct

### 10. OCR Returns Gibberish Text
**Symptoms**: Detected text is unreadable
**Cause**: Poor image quality or OCR model issues
**Solution**:
- Improve image resolution (plate should be large in frame)
- Ensure good lighting
- Clean up noise with preprocessing
- Consider training custom OCR model

## Debugging Steps

### Step 1: Check Logs
```bash
# Vercel logs
vercel logs <project-url>

# Local logs
python3 app.py  # Check console output
```

### Step 2: Test Locally First
```bash
# Install dependencies
pip install -r requirements.txt

# Validate environment
python3 validate_env.py

# Run app
python3 app.py

# Test in browser
curl http://localhost:5000/
```

### Step 3: Verify Configuration
```bash
# Check vercel.json is valid
python3 -m json.tool vercel.json

# Check for syntax errors
python3 -m py_compile api/index.py app.py
```

### Step 4: Check Environment Variables
In Vercel dashboard:
1. Go to Settings
2. Check Environment Variables section
3. Ensure all required variables are set
4. Redeploy after changes

### Step 5: Monitor Execution
- Check function duration (should be < 30s for most images)
- Monitor memory usage (should be < 3GB)
- Check error rates in dashboard
- Look for patterns in failed requests

## Performance Optimization

### Image Processing
- Resize images before processing
- Use grayscale for cascade detection
- Limit cascade search area
- Cache results when possible

### Model Loading
- Load models at startup, not per request
- Use smaller model variants
- Consider quantization for faster inference
- Precompile Python modules

### Memory Management
- Delete temporary files after processing
- Use generators for large datasets
- Clear caches between requests
- Monitor memory trends

## Monitoring in Production

### What to Watch
1. Error rate (target: < 0.1%)
2. Function duration (target: < 10s)
3. Memory usage (target: < 2GB)
4. Cold start times (target: < 30s)

### Setting Up Alerts
In Vercel dashboard:
1. Go to Settings → Observability
2. Set up email alerts for:
   - High error rate
   - Slow function execution
   - Memory limit warnings

## Getting Help

If issues persist:
1. Check Vercel documentation: https://vercel.com/docs
2. Review error messages in Vercel logs
3. Test locally first before deploying
4. Search Vercel community forum
5. Check OpenCV and Flask documentation

## Emergency Rollback

If deployment breaks production:
1. Go to Vercel dashboard
2. Select deployment from list
3. Click three dots → Promote to Production
4. Select previous working version
5. Production is instantly reverted
