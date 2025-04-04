import cv2
import numpy as np
import os
import logging
import urllib.request
import time
from pathlib import Path

# Import model trainer if available
try:
    import model_trainer
    MODEL_TRAINER_AVAILABLE = True
except ImportError:
    MODEL_TRAINER_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants - Updated URLs to reliable sources
CASCADE_URL = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_russian_plate_number.xml"
# Alternate cascade
ALT_CASCADE_URL = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_licence_plate_rus_16stages.xml"

# File paths
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
CASCADE_PATH = os.path.join(MODEL_DIR, 'haarcascade_license_plate.xml')
ALT_CASCADE_PATH = os.path.join(MODEL_DIR, 'haarcascade_alt_license_plate.xml')
CUSTOM_MODEL_PATH = os.path.join(MODEL_DIR, 'indian_plate_classifier.pkl')

# Check if ultralytics is available for YOLO model
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    # Best YOLO model for license plate detection (small license plate model)
    YOLO_MODEL_PATH = os.path.join(MODEL_DIR, 'license_plate_detector.pt')
    
    # For small model from HuggingFace or similar sources
    YOLO_MODEL_URL = "https://github.com/quangnhat185/Plate_detect_and_recognize/raw/master/weights/best.pt"
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("Ultralytics not available. YOLO detection will be disabled.")

def download_model_files():
    """
    Download model files if they don't exist
    Returns:
        bool: Success status
    """
    # Create model directory if it doesn't exist
    os.makedirs(MODEL_DIR, exist_ok=True)
    success = True
    
    try:
        # Download cascade file if it doesn't exist
        if not os.path.exists(CASCADE_PATH):
            logger.debug(f"Downloading cascade file from {CASCADE_URL}")
            try:
                urllib.request.urlretrieve(CASCADE_URL, CASCADE_PATH)
                logger.debug("Cascade file downloaded successfully")
            except Exception as e:
                logger.error(f"Error downloading main cascade: {e}")
                success = False
        
        # Download alternative cascade as backup
        if not os.path.exists(ALT_CASCADE_PATH):
            logger.debug(f"Downloading alternative cascade from {ALT_CASCADE_URL}")
            try:
                urllib.request.urlretrieve(ALT_CASCADE_URL, ALT_CASCADE_PATH)
                logger.debug("Alternative cascade downloaded successfully")
            except Exception as e:
                logger.error(f"Error downloading alternative cascade: {e}")
                success = False
        
        # Download YOLO model if available and not exists
        if YOLO_AVAILABLE and not os.path.exists(YOLO_MODEL_PATH):
            logger.debug(f"Downloading YOLO model from {YOLO_MODEL_URL}")
            try:
                urllib.request.urlretrieve(YOLO_MODEL_URL, YOLO_MODEL_PATH)
                logger.debug("YOLO model downloaded successfully")
            except Exception as e:
                logger.error(f"Error downloading YOLO model: {e}")
                success = False
        
        return success
    except Exception as e:
        logger.error(f"Error in download_model_files: {e}")
        return False

def detect_plate_with_yolo(image):
    """
    Detect number plate using YOLOv8 model if available.
    
    Args:
        image: OpenCV image
        
    Returns:
        plate_image: Cropped plate image
        plate_bbox: Bounding box coordinates
    """
    if not YOLO_AVAILABLE:
        return None, None
    
    # Download model if needed
    if not os.path.exists(YOLO_MODEL_PATH):
        if not download_model_files():
            return None, None
    
    try:
        # Save the image temporarily (YOLO model needs a file path)
        temp_img_path = os.path.join(MODEL_DIR, "temp_image.jpg")
        cv2.imwrite(temp_img_path, image)
        
        # Load the YOLO model
        model = YOLO(YOLO_MODEL_PATH)
        
        # Run inference
        results = model(temp_img_path)
        
        # Process results
        if len(results) > 0 and len(results[0].boxes.data) > 0:
            # Get the box with highest confidence
            boxes = results[0].boxes.data.cpu().numpy()
            
            # Sort by confidence (last column)
            boxes = boxes[boxes[:, 4].argsort()[::-1]]
            
            # Get best box
            best_box = boxes[0]
            
            # Extract coordinates
            x1, y1, x2, y2 = map(int, best_box[:4])
            
            # Convert to x, y, w, h format
            x, y = x1, y1
            w, h = x2 - x1, y2 - y1
            
            # Extract the plate region
            plate_image = image[y:y+h, x:x+w]
            
            # Remove temp image
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
            
            return plate_image, [x, y, w, h]
        
        # Remove temp image
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
    
    except Exception as e:
        logger.error(f"Error in YOLO detection: {str(e)}")
        # Clean up temp image if exists
        if os.path.exists(os.path.join(MODEL_DIR, "temp_image.jpg")):
            os.remove(os.path.join(MODEL_DIR, "temp_image.jpg"))
    
    return None, None

def detect_plate_with_custom_model(image):
    """
    Detect number plate using the custom trained model for Indian plates.
    
    Args:
        image: OpenCV image
        
    Returns:
        plate_image: Cropped plate image
        plate_bbox: Bounding box coordinates
    """
    # Check if custom model is available
    if not MODEL_TRAINER_AVAILABLE or not os.path.exists(CUSTOM_MODEL_PATH):
        logger.debug("Custom model not available")
        return None, None
    
    try:
        # Load the model
        model, label_encoder = model_trainer.load_trained_model(CUSTOM_MODEL_PATH)
        if model is None:
            logger.warning("Failed to load custom model")
            return None, None
        
        # Use contour detection to get candidate regions
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply Sobel edge detection optimized for Indian plates
        sobel_x = cv2.Sobel(blur, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(blur, cv2.CV_64F, 0, 1, ksize=3)
        abs_sobel_x = cv2.convertScaleAbs(sobel_x)
        abs_sobel_y = cv2.convertScaleAbs(sobel_y)
        edges = cv2.addWeighted(abs_sobel_x, 0.7, abs_sobel_y, 0.3, 0)  # More weight to horizontal edges for plates
        
        # Apply threshold
        _, thresh = cv2.threshold(edges, 150, 255, cv2.THRESH_BINARY)
        
        # Apply morphological operations to enhance plate regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 5))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by aspect ratio and area - adjusted for Indian plates
        possible_plates = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            aspect_ratio = float(w) / h
            
            # Indian plates typically have aspect ratio between 2.0 and 5.0
            if area > 1000 and 2.0 < aspect_ratio < 6.0:
                possible_plates.append((x, y, w, h))
        
        if not possible_plates:
            logger.debug("No candidate plate regions found")
            return None, None
        
        # Score each candidate using the model
        best_score = -1
        best_plate = None
        
        for x, y, w, h in possible_plates:
            # Add margin around the plate
            margin_x = int(w * 0.05)
            margin_y = int(h * 0.1)
            
            x1 = max(0, x - margin_x)
            y1 = max(0, y - margin_y)
            x2 = min(image.shape[1], x + w + margin_x)
            y2 = min(image.shape[0], y + h + margin_y)
            
            # Extract plate region
            plate_region = image[y1:y2, x1:x2]
            
            # Check if region is valid
            if plate_region.size == 0:
                continue
                
            try:
                # Convert to features using the same preprocessing as training
                features = model_trainer.preprocess_image_for_training(plate_region)
                
                if features is None:
                    continue
                
                # Get prediction confidence
                prediction_proba = model.predict_proba([features])[0]
                score = np.mean(prediction_proba)  # Average confidence across classes
                
                logger.debug(f"Plate candidate score: {score:.4f}")
                
                if score > best_score:
                    best_score = score
                    best_plate = (x1, y1, x2-x1, y2-y1)
            except Exception as e:
                logger.error(f"Error scoring plate candidate: {str(e)}")
        
        # Use the best plate if score is above threshold
        if best_plate and best_score > 0.3:  # Lower threshold since this is just for detection
            x, y, w, h = best_plate
            plate_image = image[y:y+h, x:x+w].copy()
            return plate_image, [x, y, w, h]
        
    except Exception as e:
        logger.error(f"Error in custom model detection: {str(e)}")
    
    return None, None

def detect_indian_plate_with_ind_marker(image):
    """
    Specifically detect Indian license plates with "IND" marker based on color and shape analysis.
    
    Args:
        image: OpenCV image
        
    Returns:
        plate_image: Cropped plate image
        plate_bbox: Bounding box coordinates
    """
    try:
        # Make a copy to avoid modifying the original
        img = image.copy()
        
        # Convert to HSV color space for better color segmentation
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Define white range for license plate background (typical for Indian plates)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 30, 255])
        
        # Create mask for white regions
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Apply morphological operations to enhance plate regions
        kernel = np.ones((5, 5), np.uint8)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours in the white mask
        contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size and aspect ratio specific to Indian plates
        possible_plates = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            aspect_ratio = float(w) / h
            
            # Indian plates with IND marker typically have aspect ratio between 3.0 and 6.0
            # and are relatively large in the image
            if area > 5000 and 3.0 < aspect_ratio < 6.0:
                # Calculate the relative size in the image
                img_area = img.shape[0] * img.shape[1]
                relative_size = area / img_area
                
                # Plates usually occupy a reasonable portion of the image
                if 0.03 < relative_size < 0.3:
                    possible_plates.append((x, y, w, h, area))
        
        # If no plates detected with specific criteria, return None
        if not possible_plates:
            return None, None
            
        # Sort by area in descending order
        possible_plates.sort(key=lambda x: x[4], reverse=True)
        
        # Take the largest plate
        x, y, w, h, _ = possible_plates[0]
        
        # Add a small margin around the plate
        margin_x = int(w * 0.05)
        margin_y = int(h * 0.1)
        
        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)
        x2 = min(img.shape[1], x + w + margin_x)
        y2 = min(img.shape[0], y + h + margin_y)
        
        # Extract the plate image
        plate_image = img[y1:y2, x1:x2]
        
        # Return the plate and coordinates
        return plate_image, [x1, y1, x2-x1, y2-y1]
        
    except Exception as e:
        logger.error(f"Error in Indian plate with IND marker detection: {str(e)}")
        return None, None

def detect_number_plate(image):
    """
    Detect number plate in the given image using a combination of methods.
    
    Args:
        image: OpenCV image (numpy array)
        
    Returns:
        plate_image: Cropped image containing the number plate
        plate_bbox: Bounding box coordinates [x, y, w, h]
    """
    # Make a copy of the image
    img_copy = image.copy()
    
    # First try the Indian-specific detector for plates with IND marker
    try:
        logger.debug("Trying Indian plate with IND marker detection")
        plate_image, plate_bbox = detect_indian_plate_with_ind_marker(img_copy)
        
        if plate_image is not None and plate_image.size > 0:
            # Check if the plate has reasonable dimensions
            h, w = plate_image.shape[:2]
            if w > 0 and h > 0 and w > 2*h and w < 8*h and w*h > 1000:
                logger.debug("Plate detected using Indian plate with IND marker detector")
                return plate_image, plate_bbox
            else:
                logger.debug(f"Plate from Indian plate detector had invalid dimensions: {w}x{h}")
    except Exception as e:
        logger.error(f"Error in Indian plate detection: {str(e)}")
    
    # Try YOLO if available (most accurate)
    if YOLO_AVAILABLE:
        try:
            logger.debug("Trying YOLO detection")
            plate_image, plate_bbox = detect_plate_with_yolo(img_copy)
            
            if plate_image is not None and plate_image.size > 0:
                # Check if the plate has reasonable dimensions
                h, w = plate_image.shape[:2]
                if w > 0 and h > 0 and w > 2*h and w < 8*h and w*h > 1000:
                    logger.debug("Plate detected using YOLO")
                    return plate_image, plate_bbox
                else:
                    logger.debug(f"Plate from YOLO had invalid dimensions: {w}x{h}")
        except Exception as e:
            logger.error(f"Error in YOLO detection: {str(e)}")
    
    # Try custom model for Indian plates if available
    if MODEL_TRAINER_AVAILABLE and os.path.exists(CUSTOM_MODEL_PATH):
        try:
            logger.debug("Trying custom model for Indian plate detection")
            plate_image, plate_bbox = detect_plate_with_custom_model(img_copy)
            
            if plate_image is not None and plate_image.size > 0:
                # Check if the plate has reasonable dimensions
                h, w = plate_image.shape[:2]
                if w > 0 and h > 0 and w > 2*h and w < 8*h and w*h > 1000:
                    logger.debug("Plate detected using custom Indian model")
                    return plate_image, plate_bbox
                else:
                    logger.debug(f"Plate from custom model had invalid dimensions: {w}x{h}")
        except Exception as e:
            logger.error(f"Error in custom model detection: {str(e)}")
    
    # If YOLO and custom model fail or are not available, try other methods
    methods = [
        detect_plate_with_cascade,
        detect_plate_with_contours
    ]
    
    # Try each method in order until one works
    for method in methods:
        try:
            logger.debug(f"Trying detection method: {method.__name__}")
            plate_image, plate_bbox = method(img_copy)
            
            # If we found a plate and it's not empty
            if plate_image is not None and plate_image.size > 0:
                # Check if the plate has reasonable dimensions
                h, w = plate_image.shape[:2]
                if w > 0 and h > 0 and w > 2*h and w < 8*h and w*h > 1000:
                    logger.debug(f"Plate detected using {method.__name__}")
                    return plate_image, plate_bbox
                else:
                    logger.debug(f"Plate from {method.__name__} had invalid dimensions: {w}x{h}")
        except Exception as e:
            logger.error(f"Error in {method.__name__}: {str(e)}")
    
    # If all methods failed, try a more aggressive approach
    logger.debug("All specific methods failed, using fallback method")
    return detect_plate_with_opencv(image)

def detect_plate_with_cascade(image):
    """
    Detect number plate using Haar Cascade.
    
    Args:
        image: OpenCV image
        
    Returns:
        plate_image: Cropped plate image
        plate_bbox: Bounding box coordinates
    """
    # Download cascade if needed
    if not os.path.exists(CASCADE_PATH):
        if not download_model_files():
            return None, None
    
    # Load the cascade
    plate_cascade = cv2.CascadeClassifier(CASCADE_PATH)
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Detect plates
    plates = plate_cascade.detectMultiScale(gray, 1.1, 4)
    
    if len(plates) > 0:
        # Take the largest plate
        best_plate = max(plates, key=lambda x: x[2]*x[3])
        x, y, w, h = best_plate
        
        # Ensure coordinates are within image bounds
        height, width = image.shape[:2]
        x = max(0, x)
        y = max(0, y)
        w = min(width - x, w)
        h = min(height - y, h)
        
        # Extract the plate region
        plate_image = image[y:y+h, x:x+w]
        
        return plate_image, [x, y, w, h]
    
    return None, None

def detect_plate_with_contours(image):
    """
    Detect number plate using contour detection.
    
    Args:
        image: OpenCV image
        
    Returns:
        plate_image: Cropped plate image
        plate_bbox: Bounding box coordinates
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply Sobel edge detection
    sobel_x = cv2.Sobel(blur, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(blur, cv2.CV_64F, 0, 1, ksize=3)
    abs_sobel_x = cv2.convertScaleAbs(sobel_x)
    abs_sobel_y = cv2.convertScaleAbs(sobel_y)
    edges = cv2.addWeighted(abs_sobel_x, 0.5, abs_sobel_y, 0.5, 0)
    
    # Apply threshold
    _, thresh = cv2.threshold(edges, 150, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours by area and aspect ratio
    possible_plates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        aspect_ratio = float(w) / h
        
        # Filter by size and aspect ratio (license plates are usually rectangular)
        if area > 1000 and 2.0 < aspect_ratio < 6.0:
            possible_plates.append((x, y, w, h))
    
    # If possible plates are found, return the largest one
    if possible_plates:
        # Sort by area (w*h) in descending order
        possible_plates.sort(key=lambda box: box[2] * box[3], reverse=True)
        x, y, w, h = possible_plates[0]
        
        # Ensure coordinates are within image bounds
        height, width = image.shape[:2]
        x = max(0, x)
        y = max(0, y)
        w = min(width - x, w)
        h = min(height - y, h)
        
        # Extract the plate region
        plate_image = image[y:y+h, x:x+w]
        
        return plate_image, [x, y, w, h]
    
    return None, None

def detect_plate_with_opencv(image):
    """
    Detect number plate using traditional OpenCV methods.
    This is a fallback method when the YOLO model is unavailable.
    
    Args:
        image: OpenCV image
        
    Returns:
        plate_image: Cropped plate image
        plate_bbox: Bounding box coordinates
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply Sobel edge detection
    sobel_x = cv2.Sobel(blur, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(blur, cv2.CV_64F, 0, 1, ksize=3)
    abs_sobel_x = cv2.convertScaleAbs(sobel_x)
    abs_sobel_y = cv2.convertScaleAbs(sobel_y)
    edges = cv2.addWeighted(abs_sobel_x, 0.5, abs_sobel_y, 0.5, 0)
    
    # Apply threshold
    _, thresh = cv2.threshold(edges, 150, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours by area and aspect ratio
    possible_plates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        aspect_ratio = float(w) / h
        
        # Filter by size and aspect ratio (license plates are usually rectangular)
        if area > 1000 and 2.0 < aspect_ratio < 6.0:
            possible_plates.append((x, y, w, h))
    
    # If possible plates are found, return the largest one
    if possible_plates:
        # Sort by area (w*h) in descending order
        possible_plates.sort(key=lambda box: box[2] * box[3], reverse=True)
        x, y, w, h = possible_plates[0]
        
        # Ensure coordinates are within image bounds
        height, width = image.shape[:2]
        x = max(0, x)
        y = max(0, y)
        w = min(width - x, w)
        h = min(height - y, h)
        
        # Extract the plate region
        plate_image = image[y:y+h, x:x+w]
        
        return plate_image, [x, y, w, h]
    
    # If no plates detected, return a portion of the image that might contain the plate
    height, width = image.shape[:2]
    
    # Assume plate might be in the lower half of the image
    y = height // 2
    h = height // 3
    x = width // 4
    w = width // 2
    
    plate_image = image[y:y+h, x:x+w]
    
    return plate_image, [x, y, w, h]
