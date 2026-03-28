# Deployment Guide

## Prerequisites
- Vercel account (https://vercel.com)
- GitHub account with repository access
- Git installed locally

## Deploying to Vercel

### Step 1: Prepare Your Repository
The project is already set up with the necessary configuration files:
- `vercel.json` - Vercel deployment configuration
- `build.sh` - Build script for system dependencies
- `requirements.txt` - Python dependencies
- `api/index.py` - Vercel serverless handler

### Step 2: Push Changes to GitHub
```bash
git add .
git commit -m "Add deployment configuration"
git push origin main
```

### Step 3: Deploy via Vercel Dashboard

1. Go to https://vercel.com/dashboard
2. Click "Add New..." → "Project"
3. Select "Import Git Repository"
4. Select your **Aashish-Chandr/Indian-Vehicle-Number-Plate-Detector** repository
5. Click "Import"

### Step 4: Configure Environment Variables
Before deploying, set up environment variables:

1. In the "Configure Project" section, add the following environment variables:
   - `FLASK_ENV` = `production`
   - `FLASK_DEBUG` = `0`
   - `KAGGLE_USERNAME` = Your Kaggle username (if using Kaggle API)
   - `KAGGLE_KEY` = Your Kaggle API key (if using Kaggle API)
   - `SESSION_SECRET` = A secure random string for Flask sessions

2. Click "Deploy"

### Step 5: Monitor Deployment
- Vercel will automatically build and deploy your application
- Check the Deployments tab for build logs and status
- Once complete, you'll receive a deployment URL (https://your-app.vercel.app)

## Environment Variables Reference

Create a `.env` file locally with the following variables:

```env
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=0

# Session Security
SESSION_SECRET=your-secure-random-string-here

# Kaggle API (Optional)
KAGGLE_USERNAME=your-kaggle-username
KAGGLE_KEY=your-kaggle-api-key

# File Upload Configuration
MAX_UPLOAD_SIZE=5242880  # 5MB in bytes

# Model Configuration
UPLOAD_FOLDER=/tmp/uploads
DETECTION_FOLDER=/tmp/detections
```

## System Dependencies
The build script automatically installs:
- `libsm6` - System library for OpenCV
- `libxext6` - X11 extension library
- `libxrender-dev` - X11 rendering library
- `tesseract-ocr` - OCR engine
- `libtesseract-dev` - Tesseract development files

## API Endpoints

After deployment, the following endpoints are available:

- `GET /` - Main web interface
- `POST /upload` - Upload and process image
- `GET /maharashtra_test` - Maharashtra number plate test page
- `GET /download_image/<path>` - Download detected plate image
- `POST /train` - Train model (if enabled)
- `POST /maharashtra_detect` - Detect Maharashtra number plates

## Troubleshooting

### Build Fails
- Check build logs in Vercel dashboard
- Ensure all dependencies in `requirements.txt` are compatible with Python 3.11
- Verify system dependencies are installed via `build.sh`

### Application Crashes
- Check function logs in Vercel dashboard
- Verify environment variables are set correctly
- Ensure upload folders have write permissions

### Import Errors
- Make sure `api/index.py` is correctly configured
- Verify all Python modules are in `requirements.txt`

### File Upload Issues
- Check maximum file size limit (default: 5MB)
- Ensure `/tmp` directory has sufficient space
- Verify MIME type restrictions in app

## Local Development

### Setup
```bash
# Clone repository
git clone https://github.com/Aashish-Chandr/Indian-Vehicle-Number-Plate-Detector.git
cd Indian-Vehicle-Number-Plate-Detector

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install system dependencies (macOS)
brew install tesseract

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install tesseract-ocr
```

### Run Locally
```bash
# Set environment variables
export FLASK_ENV=development
export FLASK_DEBUG=1
export SESSION_SECRET=dev-secret-key

# Run the application
python app.py
```

The application will be available at `http://localhost:5000`

## Performance Considerations

- **Model Loading**: Models are loaded once at startup
- **Image Processing**: Processing time depends on image size
- **OCR**: Tesseract OCR can be slow for large images
- **Memory**: Keep uploaded files under 5MB to avoid timeout issues

## Security Best Practices

1. **Session Secret**: Use a strong, random string for `SESSION_SECRET`
2. **File Upload**: Validate all uploaded files
3. **Environment Variables**: Never commit sensitive data to git
4. **HTTPS**: Vercel automatically provides HTTPS
5. **CORS**: Configure CORS settings if needed

## Support

For issues with:
- **Vercel Deployment**: See https://vercel.com/docs
- **Flask**: See https://flask.palletsprojects.com
- **Project-specific**: Open an issue on GitHub

## Additional Resources

- [Vercel Python Documentation](https://vercel.com/docs/functions/python)
- [Flask Deployment Guide](https://flask.palletsprojects.com/deployment/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
