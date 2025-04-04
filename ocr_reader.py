import cv2
import numpy as np
import pytesseract
import re
import logging
import platform
import os
import tempfile

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check if pytesseract executable needs to be specified
if platform.system() == 'Windows':
    # On Windows, pytesseract needs to know the location of tesseract.exe
    # Default location is Program Files, but you need to have it installed
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_plate(plate_image):
    """
    Extract text from the plate image using OCR.
    
    Args:
        plate_image: OpenCV image of the number plate
        
    Returns:
        text: Extracted text from the plate
    """
    try:
        # Preprocess the image for better OCR results
        processed_image = preprocess_plate_image(plate_image)
        
        # Use Tesseract to extract text
        # Configure tesseract parameters for license plate recognition
        custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
        
        # Extract text
        text = pytesseract.image_to_string(processed_image, config=custom_config).strip()
        
        # Clean up the text
        text = clean_plate_text(text)
        
        logger.debug(f"Extracted text: {text}")
        
        return text
    except Exception as e:
        logger.error(f"Error in OCR: {str(e)}")
        return "Could not read plate text"

def preprocess_plate_image(plate_image):
    """
    Preprocess the plate image to improve OCR accuracy.
    
    Args:
        plate_image: OpenCV image of the plate
        
    Returns:
        processed_image: Preprocessed image ready for OCR
    """
    # Convert to grayscale
    gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
    
    # Apply bilateral filter to remove noise while keeping edges sharp
    bilateral = cv2.bilateralFilter(gray, 11, 17, 17)
    
    # Apply adaptive threshold
    thresh = cv2.adaptiveThreshold(bilateral, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY_INV, 11, 2)
    
    # Dilate to connect components
    kernel = np.ones((3,3), np.uint8)
    dilate = cv2.dilate(thresh, kernel, iterations=1)
    
    # Erode to remove small noise
    erode = cv2.erode(dilate, kernel, iterations=1)
    
    # Invert back for OCR (white text on black background)
    processed = cv2.bitwise_not(erode)
    
    # Resize for better OCR
    processed = cv2.resize(processed, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    return processed

def clean_plate_text(text):
    """
    Clean the OCR output to format it as a valid Indian license plate.
    
    Args:
        text: Raw OCR text
        
    Returns:
        cleaned_text: Formatted license plate text
    """
    # Remove whitespace and special characters
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[^\w\s-]', '', text)
    
    # Convert to uppercase
    text = text.upper()
    
    # Try to match Indian license plate format (e.g., MH12AB1234)
    # Format: 2 letters (state code) + 2 digits (district code) + 2 letters + 4 digits
    pattern = r'([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{1,4})'
    match = re.search(pattern, text)
    
    if match:
        # Format the matched text
        plate_text = match.group(1)
        return plate_text
    
    # If no match found, return the original cleaned text
    return text
