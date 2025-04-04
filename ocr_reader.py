import cv2
import numpy as np
import pytesseract
import re
import logging
import platform
import os
import tempfile
import Levenshtein
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check if tesseract is installed and set the path
def check_tesseract_installation():
    """Check if tesseract is installed and configure the path"""
    if platform.system() == 'Windows':  # Windows
        # On Windows, pytesseract needs to know the location of tesseract.exe
        if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            return True
    else:  # Linux/Mac
        # Check common locations
        possible_paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/opt/homebrew/bin/tesseract',
            '/nix/store/2paqyrmfbzasca0qjhmq2pw2g6jp5y7q-tesseract-5.3.0/bin/tesseract'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.debug(f"Found tesseract at: {path}")
                pytesseract.pytesseract.tesseract_cmd = path
                return True
    
    # If not found in common locations
    try:
        # Try to find tesseract in PATH
        import subprocess
        result = subprocess.run(['which', 'tesseract'], capture_output=True, text=True)
        if result.returncode == 0:
            tesseract_path = result.stdout.strip()
            logger.debug(f"Found tesseract at: {tesseract_path}")
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            return True
    except Exception as e:
        logger.error(f"Error finding tesseract: {e}")
    
    logger.warning("Tesseract not found. OCR functionality may be limited.")
    return False

# Check tesseract installation on module import
check_tesseract_installation()

def extract_text_from_plate(plate_image, plate_type='indian'):
    """
    Extract text from the plate image using OCR with multiple preprocessing techniques.
    
    Args:
        plate_image: OpenCV image of the number plate
        plate_type: Type of license plate to look for ('indian', 'european', 'american', etc.)
        
    Returns:
        text: Extracted text from the plate
    """
    try:
        # Check if plate image is valid
        if plate_image is None or plate_image.size == 0:
            logger.error("Invalid plate image for OCR")
            return "Could not read plate text"
        
        # Try multiple preprocessing methods and configurations
        ocr_results = []
        confidences = []
        
        # Standard preprocessing
        processed_image1 = preprocess_plate_image(plate_image)
        
        # Alternative preprocessing with more aggressive thresholding
        processed_image2 = preprocess_plate_image_alternative(plate_image)
        
        # Resized preprocessing
        processed_image3 = preprocess_plate_image_resized(plate_image)
        
        # Try different PSM modes for better recognition
        psm_modes = [7, 8, 6, 3]  # Order of likely effectiveness for license plates
        
        for img in [processed_image1, processed_image2, processed_image3]:
            for psm in psm_modes:
                try:
                    # Configure tesseract parameters
                    custom_config = f'--oem 3 --psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
                    
                    # Extract text
                    text = pytesseract.image_to_string(img, config=custom_config).strip()
                    
                    # Clean up the text
                    cleaned_text = clean_plate_text(text, plate_type)
                    
                    # If we got meaningful text
                    if cleaned_text and len(cleaned_text) >= 4:
                        # Calculate a simple confidence score based on length and content
                        confidence = calculate_text_confidence(cleaned_text, plate_type)
                        
                        # Add to results
                        if cleaned_text not in ocr_results:
                            ocr_results.append(cleaned_text)
                            confidences.append(confidence)
                            
                            logger.debug(f"OCR result (PSM {psm}): {cleaned_text}, confidence: {confidence}")
                except Exception as e:
                    logger.error(f"Error in OCR with PSM {psm}: {str(e)}")
        
        # If we have results, return the one with highest confidence
        if ocr_results:
            best_idx = confidences.index(max(confidences))
            best_text = ocr_results[best_idx]
            logger.debug(f"Best OCR result: {best_text}")
            return best_text
        
        # If all tries failed
        return "Could not read plate text"
    except Exception as e:
        logger.error(f"Error in OCR: {str(e)}")
        return "Could not read plate text"

def calculate_text_confidence(text, plate_type='indian'):
    """
    Calculate a confidence score for OCR result.
    
    Args:
        text: OCR recognized text
        plate_type: Type of license plate (indian, european, american, etc.)
        
    Returns:
        confidence: Score between 0 and 1
    """
    # First general check for all plate types - must have both letters and numbers
    has_letters = bool(re.search(r'[A-Z]', text))
    has_numbers = bool(re.search(r'[0-9]', text))
    
    if not (has_letters and has_numbers):
        return 0.1  # Very low confidence if missing either letters or numbers
    
    # Indian plates check (e.g., MH12AB1234)
    if plate_type.lower() == 'indian':
        if re.match(r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$', text):
            return 0.95  # Very high confidence for perfect Indian pattern match
        
        # Check for partial matches to known Indian formats
        if re.match(r'^[A-Z]{2}\d{1,2}', text):  # Has state code and district code
            return 0.8
    
    # European plates check
    elif plate_type.lower() == 'european':
        # Check for common European formats
        if re.match(r'^[A-Z]{1,3}[\s-][A-Z]{1,3}[\s-][0-9]{1,4}$', text):  # German-like
            return 0.95
        if re.match(r'^[A-Z]{2}[\s-][0-9]{3}[\s-][A-Z]{2}$', text):  # French-like
            return 0.95
        if re.match(r'^[A-Z]{1,3}[\s-][0-9]{2,5}$', text):  # Simple format
            return 0.9
    
    # American plates check
    elif plate_type.lower() == 'american':
        if re.match(r'^[A-Z]{3}[0-9]{3,4}$', text):  # Common format ABC123
            return 0.95
        if re.match(r'^[0-9]{3}[\s-][A-Z]{3}$', text):  # Format 123-ABC
            return 0.95
        if re.match(r'^[A-Z]{1,3}[\s-][0-9]{3,4}$', text):  # Format AB-1234
            return 0.9
    
    # General checks for all plate types based on length and content
    length = len(text)
    
    # Most license plates worldwide are between 5-10 characters
    if 5 <= length <= 10:
        return 0.7
    # Slightly longer/shorter plates are still possible
    elif 4 <= length <= 12:
        return 0.5
    # Very long or very short results are less likely to be valid
    else:
        return 0.3

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

def preprocess_plate_image_alternative(plate_image):
    """
    Alternative preprocessing method using different thresholding technique.
    
    Args:
        plate_image: OpenCV image of the plate
        
    Returns:
        processed_image: Preprocessed image ready for OCR
    """
    # Convert to grayscale
    gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
    
    # Normalize lighting
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    # Apply Gaussian blur to reduce noise
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply Otsu's thresholding
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Apply morphological operations
    kernel = np.ones((3,3), np.uint8)
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # Resize for better OCR
    processed = cv2.resize(closing, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    return processed

def preprocess_plate_image_resized(plate_image):
    """
    Preprocessing with different resize and border padding.
    
    Args:
        plate_image: OpenCV image of the plate
        
    Returns:
        processed_image: Preprocessed image ready for OCR
    """
    # Convert to grayscale
    gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
    
    # Add border to help with character extraction
    border_size = 10
    gray_bordered = cv2.copyMakeBorder(gray, border_size, border_size, border_size, border_size,
                                     cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    # Increase contrast
    alpha = 1.5  # Contrast control
    beta = 10    # Brightness control
    adjusted = cv2.convertScaleAbs(gray_bordered, alpha=alpha, beta=beta)
    
    # Apply Gaussian blur to reduce noise
    blur = cv2.GaussianBlur(adjusted, (3, 3), 0)
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                 cv2.THRESH_BINARY, 11, 2)
    
    # Resize larger for better OCR
    processed = cv2.resize(thresh, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    
    return processed

def clean_plate_text(text, plate_type='indian'):
    """
    Clean the OCR output to format it as a valid license plate.
    
    Args:
        text: Raw OCR text
        plate_type: Type of license plate (indian, european, american, etc.)
        
    Returns:
        cleaned_text: Formatted license plate text
    """
    # Remove whitespace and special characters
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[^\w\s-]', '', text)
    
    # Convert to uppercase
    text = text.upper()
    
    # Common OCR misreads and fixes (specific to license plates)
    text = text.replace('O', '0').replace('I', '1').replace('S', '5').replace('Z', '2')
    
    if plate_type.lower() == 'indian':
        # Try to match Indian license plate format (e.g., MH12AB1234)
        # Format: 2 letters (state code) + 2 digits (district code) + 2-3 letters + 1-4 digits
        pattern = r'([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{1,4})'
        match = re.search(pattern, text)
        
        if match:
            # Format the matched text
            plate_text = match.group(1)
            # Remove any remaining spaces
            plate_text = re.sub(r'\s+', '', plate_text)
            return plate_text
        
        # If no match found, try to construct a reasonable license plate format
        letters = re.findall(r'[A-Z]+', text)
        numbers = re.findall(r'[0-9]+', text)
        
        if len(letters) >= 2 and len(numbers) >= 2:
            try:
                # Try to construct in right format
                constructed = letters[0][:2] + numbers[0][:2] + letters[-1][:2] + numbers[-1][:4]
                return constructed
            except:
                pass
    
    elif plate_type.lower() == 'european':
        # Try to match European license plate formats
        # Example: German plates like "B AB 123" or French plates like "AB-123-CD"
        eu_patterns = [
            r'([A-Z]{1,3}[\s-][A-Z]{1,3}[\s-][0-9]{1,4})',  # German-like
            r'([A-Z]{2}[\s-][0-9]{3}[\s-][A-Z]{2})',        # French-like
            r'([A-Z]{1,3}[\s-][0-9]{2,5})',                 # Simple format
        ]
        
        for pattern in eu_patterns:
            match = re.search(pattern, text)
            if match:
                plate_text = match.group(1)
                # Keep the spaces/hyphens for European plates
                return plate_text
    
    elif plate_type.lower() == 'american':
        # Try to match US license plate formats (varies by state)
        # Looking for patterns like "ABC123" or "123-ABC" or "ABC-1234"
        us_patterns = [
            r'([A-Z]{3}[0-9]{3,4})',  # Example: ABC123
            r'([0-9]{3}[\s-][A-Z]{3})',  # Example: 123-ABC
            r'([A-Z]{1,3}[\s-][0-9]{3,4})' # Example: AB-1234
        ]
        
        for pattern in us_patterns:
            match = re.search(pattern, text)
            if match:
                plate_text = match.group(1)
                return plate_text
    
    # If no specific format matches or plate_type not recognized, 
    # just return alphanumeric characters
    alphanumeric_text = re.sub(r'[^A-Z0-9]', '', text)
    
    # If the text is too long, it's probably noise
    if len(alphanumeric_text) > 12:
        alphanumeric_text = alphanumeric_text[:12]
        
    return alphanumeric_text
