#!/bin/bash

# Install system dependencies for OpenCV and Tesseract
apt-get update || true
apt-get install -y --no-install-recommends \
    libsm6 \
    libxext6 \
    libxrender-dev \
    tesseract-ocr \
    libtesseract-dev \
    2>/dev/null || true

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
