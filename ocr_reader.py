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
    
    # Indian plates check with expanded patterns (e.g., MH12AB1234, DL2CAB1234, etc.)
    if plate_type.lower() == 'indian':
        # Perfect Indian license plate format
        if re.match(r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$', text):
            return 0.95  # Very high confidence
        
        # Check for partial but strong matches to known Indian formats
        if re.match(r'^[A-Z]{2}\d{1,2}[A-Z]+\d{2,4}$', text):  # Has all components but maybe wrong length
            return 0.9
            
        # Has state code, district code and some additional characters
        if re.match(r'^[A-Z]{2}\d{1,2}[A-Z0-9]+$', text):
            return 0.85
        
        # Has state code and district code (beginning is correct)
        if re.match(r'^[A-Z]{2}\d{1,2}', text):
            return 0.8
            
        # Check for specific state codes from India (increases confidence)
        indian_states = ['AP', 'AR', 'AS', 'BR', 'CG', 'GA', 'GJ', 'HR', 'HP', 
                         'JK', 'JH', 'KA', 'KL', 'MP', 'MH', 'MN', 'ML', 'MZ', 
                         'NL', 'OD', 'PB', 'RJ', 'SK', 'TN', 'TS', 'TR', 'UK', 
                         'UP', 'WB', 'AN', 'CH', 'DN', 'DD', 'DL', 'LD', 'PY']
        
        if any(text.startswith(state) for state in indian_states):
            return 0.75  # Good confidence if starts with a valid state code
    
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
    Specifically optimized for Indian plates.
    
    Args:
        plate_image: OpenCV image of the plate
        
    Returns:
        processed_image: Preprocessed image ready for OCR
    """
    # Convert to grayscale
    if len(plate_image.shape) == 3:
        gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = plate_image.copy()
    
    # Apply bilateral filter to remove noise while keeping edges sharp
    # Parameters optimized for Indian plates (less smoothing to preserve fine details)
    bilateral = cv2.bilateralFilter(gray, 9, 15, 15)
    
    # Normalize the image histogram for better contrast
    # Higher clip limit for Indian plates which may have varying contrast
    clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(bilateral)
    
    # Apply local thresholding for better handling of uneven lighting
    # Indian plates often have shadow issues
    thresh = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 15, 5  # Parameters tuned for Indian plates
    )
    
    # Apply morphological operations to clean up the result
    # Slightly larger kernel for Indian plates to better connect characters
    kernel = np.ones((3, 3), np.uint8)
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # Edge enhancement for better character definition
    kernel_sharp = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharpened = cv2.filter2D(morph, -1, kernel_sharp)
    
    # Add border for better OCR
    border_size = 10
    final = cv2.copyMakeBorder(sharpened, border_size, border_size, 
                             border_size, border_size,
                             cv2.BORDER_CONSTANT, value=255)
    
    # No resizing - maintain original resolution as requested
    return final

def preprocess_plate_image_alternative(plate_image):
    """
    Alternative preprocessing method optimized for Indian plates with high
    contrast and better edge detection.
    
    Args:
        plate_image: OpenCV image of the plate
        
    Returns:
        processed_image: Preprocessed image ready for OCR
    """
    # Convert to grayscale
    if len(plate_image.shape) == 3:
        gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = plate_image.copy()
    
    # Apply image normalization to enhance contrast
    # Normalize to full range 0-255
    normalized = cv2.normalize(gray, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    
    # Apply edge enhancement to make characters more distinct
    # Stronger sharpening for Indian plates with sometimes faded characters
    kernel = np.array([[-1,-1,-1], [-1,10,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(normalized, -1, kernel)
    
    # Apply median blur - better at preserving edges than Gaussian for Indian plates
    blur = cv2.medianBlur(sharpened, 3)
    
    # Apply Otsu's thresholding - works well for Indian plates with good contrast
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Apply morphological operations to clean up the image
    # Horizontal dilation helps with Indian plates where characters might be fading
    kernel_h = np.ones((1, 3), np.uint8)
    dilated_h = cv2.dilate(binary, kernel_h, iterations=1)
    
    # Standard closing for general cleanup
    kernel = np.ones((3, 3), np.uint8)
    closing = cv2.morphologyEx(dilated_h, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # Add border for better OCR
    border_size = 10
    bordered = cv2.copyMakeBorder(closing, border_size, border_size, 
                                border_size, border_size,
                                cv2.BORDER_CONSTANT, value=255)
    
    # No resizing - maintain original resolution as requested
    return bordered

def preprocess_plate_image_resized(plate_image):
    """
    Preprocessing specifically for Indian plates with extreme contrast adjustment
    and advanced morphological operations, but no resizing.
    
    Args:
        plate_image: OpenCV image of the plate
        
    Returns:
        processed_image: Preprocessed image ready for OCR
    """
    # Convert to grayscale
    if len(plate_image.shape) == 3:
        gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = plate_image.copy()
    
    # Add border to help with character extraction - important for OCR
    border_size = 10
    gray_bordered = cv2.copyMakeBorder(gray, border_size, border_size, border_size, border_size,
                                     cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    # Apply histogram equalization for better contrast
    # This is particularly effective for Indian plates with varying lighting
    equalized = cv2.equalizeHist(gray_bordered)
    
    # Increase contrast even more for Indian plates (which may have faded characters)
    alpha = 2.2  # Slightly stronger contrast
    beta = 10    # Increased brightness to highlight characters
    adjusted = cv2.convertScaleAbs(equalized, alpha=alpha, beta=beta)
    
    # Apply bilateral filter to smooth noise while preserving edges
    # Parameters optimized for Indian plates
    bilateral = cv2.bilateralFilter(adjusted, 7, 45, 45)
    
    # Apply local adaptive thresholding with parameters optimized for Indian plates
    thresh = cv2.adaptiveThreshold(bilateral, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                 cv2.THRESH_BINARY, 11, 2)
    
    # Apply specific morphological operations for Indian plates
    # First dilate slightly to connect broken characters (common in Indian plates)
    kernel_dilate = np.ones((2,1), np.uint8)  # Vertical dilation to connect character parts
    dilated = cv2.dilate(thresh, kernel_dilate, iterations=1)
    
    # Then apply closing to remove small holes
    kernel_close = np.ones((3,3), np.uint8)
    morph = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel_close, iterations=1)
    
    # Finally, apply opening to remove small noise
    kernel_open = np.ones((2,2), np.uint8)
    cleaned = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel_open, iterations=1)
    
    # No resizing as requested
    return cleaned

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
        # Additional cleanup specific to Indian plates
        # Common replacements for Indian plates
        text = text.replace('8', 'B').replace('B', '8', 1).replace('D', '0').replace('Q', '0')
        
        # Try to match complete Indian license plate format (e.g., MH12AB1234)
        # Format: 2 letters (state code) + 1-2 digits (district code) + 1-3 letters + 1-4 digits
        pattern = r'([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{1,4})'
        match = re.search(pattern, text)
        
        if match:
            # Format the matched text
            plate_text = match.group(1)
            # Remove any remaining spaces
            plate_text = re.sub(r'\s+', '', plate_text)
            return plate_text
            
        # Try more lenient patterns for partial matches (common in real-world OCR)
        partial_patterns = [
            r'([A-Z]{2})\s*([0-9]{1,2})\s*([A-Z]{1,3})\s*([0-9]{1,4})',  # Standard format with groups
            r'([A-Z]{2})\s*([0-9]{1,2}).*?([0-9]{1,4})',                # Just state + district + ending numbers
            r'([A-Z]{2}).*?([0-9]{3,4})'                                # Just state + any ending numbers
        ]
        
        for pattern in partial_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 4:  # Full match with all components
                    plate_text = groups[0] + groups[1] + groups[2] + groups[3]
                    return plate_text
                elif len(groups) == 3:  # State, district, and numbers, but missing letters
                    # Construct with an 'X' placeholder for the missing letter section
                    plate_text = groups[0] + groups[1] + 'X' + groups[2]
                    return plate_text
                elif len(groups) == 2:  # Just state and ending numbers
                    # For very partial matches, try to guess district from context
                    plate_text = groups[0] + '01X' + groups[1]  # Assume district 01 as fallback
                    return plate_text
        
        # If no match with patterns, try to construct from identified components
        letters = re.findall(r'[A-Z]+', text)
        numbers = re.findall(r'[0-9]+', text)
        
        if len(letters) >= 1 and len(numbers) >= 1:
            try:
                # Get first letter group (likely state code)
                state_code = letters[0][:2].ljust(2, 'X')  # Pad with X if needed
                
                # Get first number group (likely district code) - limit to 2 digits
                district_code = numbers[0][:2].ljust(1, '0')  # Ensure at least 1 digit
                
                # Get remaining letters (registration letters) - default to X if not available
                reg_letters = letters[-1][:2].ljust(1, 'X') if len(letters) > 1 else 'X'
                
                # Get remaining numbers (registration number) - default to 0000 if not available
                reg_numbers = numbers[-1][:4].ljust(4, '0') if len(numbers) > 1 else '0000'
                
                # Construct in standard Indian format
                constructed = state_code + district_code + reg_letters + reg_numbers
                return constructed
            except:
                # If construction fails, just concatenate available parts
                parts = []
                for letter_group in letters[:2]:  # Only use first two letter groups
                    parts.append(letter_group[:3])  # Limit each group to 3 chars
                for number_group in numbers[:2]:  # Only use first two number groups
                    parts.append(number_group[:4])  # Limit each group to 4 digits
                
                if parts:
                    return ''.join(parts)[:10]  # Limit to reasonable length
    
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
