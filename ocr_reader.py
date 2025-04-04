import cv2
import numpy as np
import pytesseract
import re
import os
import logging
import tempfile
import Levenshtein
from typing import Tuple, List, Optional

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def check_tesseract_installation():
    """Check if tesseract is installed and configure the path"""
    try:
        version = pytesseract.get_tesseract_version()
        logger.debug(f"Found tesseract at: {pytesseract.pytesseract.tesseract_cmd}")
        return True
    except Exception as e:
        logger.error(f"Tesseract not properly installed: {str(e)}")
        
        # Try to find tesseract in common locations
        possible_paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/opt/homebrew/bin/tesseract',
            '/nix/store/*/bin/tesseract',  # Common in replit/nix
        ]
        
        for path_pattern in possible_paths:
            if '*' in path_pattern:
                # Handle wildcard paths
                import glob
                for path in glob.glob(path_pattern):
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        logger.debug(f"Setting tesseract path to: {path}")
                        return True
            elif os.path.exists(path_pattern):
                pytesseract.pytesseract.tesseract_cmd = path_pattern
                logger.debug(f"Setting tesseract path to: {path_pattern}")
                return True
        
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
        
        # Optimize tesseract whitelist based on plate type
        whitelist = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
        
        # For Indian plates, we can be more specific about allowed characters
        if plate_type.lower() == 'indian':
            # Most Indian plates use a subset of letters and numbers
            whitelist = 'ABCDEFGHJKLMNOPQRSTUVWXYZ0123456789'
        
        # Standard preprocessing
        processed_image1 = preprocess_plate_image(plate_image)
        
        # Alternative preprocessing with more aggressive thresholding
        processed_image2 = preprocess_plate_image_alternative(plate_image)
        
        # Preprocessing with border (no resize)
        processed_image3 = preprocess_plate_image_resized(plate_image)
        
        # Try different PSM modes for better recognition
        psm_modes = [7, 8, 6, 11, 3]  # Order of likely effectiveness for license plates
                                      # 11 is sparse text which can work well for plates
        
        for idx, img in enumerate([processed_image1, processed_image2, processed_image3]):
            for psm in psm_modes:
                try:
                    # Configure tesseract parameters
                    custom_config = f'--oem 3 --psm {psm} -c tessedit_char_whitelist={whitelist}'
                    
                    # Save the processed image temporarily for easier debugging
                    temp_img_path = os.path.join(tempfile.gettempdir(), f'tess_{next(tempfile._get_candidate_names())}_input.PNG')
                    cv2.imwrite(temp_img_path, img)
                    
                    # Extract text with detailed logging
                    logger.debug(f"Running tesseract with PSM {psm}: {[pytesseract.pytesseract.tesseract_cmd, temp_img_path, temp_img_path.replace('.PNG', ''), '--oem', '3', '--psm', str(psm), '-c', f'tessedit_char_whitelist={whitelist}', 'txt']}")
                    text = pytesseract.image_to_string(temp_img_path, config=custom_config).strip()
                    
                    # Clean up the text with plate-type specific cleaning
                    cleaned_text = clean_plate_text(text, plate_type)
                    
                    # If we got meaningful text (even 3 characters might be valid for some plates)
                    if cleaned_text and len(cleaned_text) >= 3:
                        # Calculate confidence score based on plate type and content
                        confidence = calculate_text_confidence(cleaned_text, plate_type)
                        
                        # Add to results if not duplicate or if better confidence
                        duplicate_idx = -1
                        for result_idx, result in enumerate(ocr_results):
                            if result == cleaned_text:
                                duplicate_idx = result_idx
                                break
                            
                            # Check for similar results using Levenshtein distance
                            if Levenshtein.distance(result, cleaned_text) <= min(2, len(cleaned_text) // 3):
                                duplicate_idx = result_idx
                                break
                        
                        if duplicate_idx >= 0:
                            # If duplicate with higher confidence, replace
                            if confidence > confidences[duplicate_idx]:
                                confidences[duplicate_idx] = confidence
                        else:
                            # New result
                            ocr_results.append(cleaned_text)
                            confidences.append(confidence)
                            logger.debug(f"OCR result (method {idx}, PSM {psm}): {cleaned_text}, confidence: {confidence}")
                except Exception as e:
                    logger.error(f"Error in OCR with PSM {psm}: {str(e)}")
        
        # Group similar results
        if len(ocr_results) > 1:
            try:
                # Create clusters of similar results
                clusters = []
                cluster_confidences = []
                
                # Start with the highest confidence result
                sorted_indices = sorted(range(len(confidences)), key=lambda i: confidences[i], reverse=True)
                
                for idx in sorted_indices:
                    result = ocr_results[idx]
                    confidence = confidences[idx]
                    
                    # Check if similar to any existing cluster
                    found_cluster = False
                    for c_idx, cluster in enumerate(clusters):
                        # Compare with the representative item in the cluster
                        if Levenshtein.distance(result, cluster[0]) <= min(2, len(result) // 3):
                            cluster.append(result)
                            # Increase confidence of cluster with each similar result
                            cluster_confidences[c_idx] += confidence * 0.5
                            found_cluster = True
                            break
                    
                    # If not similar to any cluster, create new cluster
                    if not found_cluster:
                        clusters.append([result])
                        cluster_confidences.append(confidence)
                
                # Select the cluster with highest confidence
                if clusters:
                    best_cluster_idx = cluster_confidences.index(max(cluster_confidences))
                    best_result = clusters[best_cluster_idx][0]  # Use the representative item
                    
                    # Clear results and add only the winner
                    ocr_results = [best_result]
                    confidences = [cluster_confidences[best_cluster_idx]]
            except Exception as e:
                logger.error(f"Error in cluster analysis: {str(e)}")
        
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
    
    # Normalize the image histogram for better contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(bilateral)
    
    # Apply Otsu's thresholding for better binarization
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Fine-tune the threshold to improve character definition
    # Apply morphological operations to clean up the result
    kernel = np.ones((2, 2), np.uint8)
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # No resizing - maintain original resolution
    return morph

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
    
    # Apply edge enhancement to make characters more distinct
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(gray, -1, kernel)
    
    # Apply Gaussian blur to reduce noise but maintain character edges
    blur = cv2.GaussianBlur(sharpened, (3, 3), 0)
    
    # Adaptive thresholding for better handling of lighting variations
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                               cv2.THRESH_BINARY, 11, 3)
    
    # Apply morphological operations to clean up the image
    kernel = np.ones((2,2), np.uint8)
    closing = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # No resizing - maintain original resolution
    return closing

def preprocess_plate_image_resized(plate_image):
    """
    Preprocessing with border padding but no resizing.
    
    Args:
        plate_image: OpenCV image of the plate
        
    Returns:
        processed_image: Preprocessed image ready for OCR
    """
    # Convert to grayscale
    gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
    
    # Add border to help with character extraction - important for OCR
    border_size = 10
    gray_bordered = cv2.copyMakeBorder(gray, border_size, border_size, border_size, border_size,
                                     cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    # Increase contrast for better character definition
    alpha = 2.0  # Contrast control
    beta = 5     # Brightness control
    adjusted = cv2.convertScaleAbs(gray_bordered, alpha=alpha, beta=beta)
    
    # Apply bilateral filter to smooth noise while preserving edges
    bilateral = cv2.bilateralFilter(adjusted, 9, 75, 75)
    
    # Apply local adaptive thresholding
    thresh = cv2.adaptiveThreshold(bilateral, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                 cv2.THRESH_BINARY, 13, 4)
    
    # Apply morphological closing to connect nearby components
    kernel = np.ones((2,2), np.uint8)
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # No resizing as requested
    return morph

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
