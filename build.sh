#!/bin/bash
set -e

echo "Starting build process..."

# Update package manager
echo "Updating package manager..."
apt-get update || true

# Install system dependencies for OpenCV and Tesseract
echo "Installing system dependencies..."
apt-get install -y --no-install-recommends \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libglib2.0-0 \
    tesseract-ocr \
    libtesseract-dev \
    2>/dev/null || true

# Clean up apt cache
apt-get clean
rm -rf /var/lib/apt/lists/*

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Validate environment
echo "Validating environment..."
python3 validate_env.py || true

echo "Build process completed successfully!"
