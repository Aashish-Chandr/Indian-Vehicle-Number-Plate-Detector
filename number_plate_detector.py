import cv2
import numpy as np
import os
import logging
import urllib.request

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
MODEL_URL = "https://github.com/parvatijay2901/Automatic-Number-plate-detection-for-Indian-vehicles/raw/main/model/yolov3_training_last.weights"
CONFIG_URL = "https://github.com/parvatijay2901/Automatic-Number-plate-detection-for-Indian-vehicles/raw/main/model/yolov3_testing.cfg"

# File paths
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yolov3_training_last.weights')
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yolov3_testing.cfg')

def download_model_files():
    """Download model files if they don't exist"""
    try:
        # Download weights file if it doesn't exist
        if not os.path.exists(MODEL_PATH):
            logger.debug(f"Downloading model weights from {MODEL_URL}")
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            logger.debug("Model weights downloaded successfully")
        
        # Download config file if it doesn't exist
        if not os.path.exists(CONFIG_PATH):
            logger.debug(f"Downloading model config from {CONFIG_URL}")
            urllib.request.urlretrieve(CONFIG_URL, CONFIG_PATH)
            logger.debug("Model config downloaded successfully")
    except Exception as e:
        logger.error(f"Error downloading model files: {str(e)}")
        # Fallback to default method if files can't be downloaded
        return False
    
    return True

def detect_number_plate(image):
    """
    Detect number plate in the given image using YOLOv3 model.
    
    Args:
        image: OpenCV image (numpy array)
        
    Returns:
        plate_image: Cropped image containing the number plate
        plate_bbox: Bounding box coordinates [x, y, w, h]
    """
    try:
        # Try to load the YOLOv3 model
        if os.path.exists(MODEL_PATH) and os.path.exists(CONFIG_PATH):
            logger.debug("Loading YOLO model for plate detection")
            net = cv2.dnn.readNet(MODEL_PATH, CONFIG_PATH)
            
            # Get detection using YOLO
            plate_image, plate_bbox = detect_plate_with_yolo(image, net)
            
            if plate_image is not None:
                return plate_image, plate_bbox
        else:
            # Try to download model files
            logger.debug("Model files not found, attempting to download")
            if download_model_files():
                # Retry with downloaded model
                net = cv2.dnn.readNet(MODEL_PATH, CONFIG_PATH)
                plate_image, plate_bbox = detect_plate_with_yolo(image, net)
                
                if plate_image is not None:
                    return plate_image, plate_bbox
        
        # Fallback to traditional CV methods if YOLO model is unavailable or fails
        logger.debug("Falling back to traditional OpenCV methods")
        return detect_plate_with_opencv(image)
    
    except Exception as e:
        logger.error(f"Error in plate detection: {str(e)}")
        # Fallback to OpenCV method
        return detect_plate_with_opencv(image)

def detect_plate_with_yolo(image, net):
    """
    Detect number plate using YOLOv3 model.
    
    Args:
        image: OpenCV image
        net: Loaded YOLOv3 network
        
    Returns:
        plate_image: Cropped plate image
        plate_bbox: Bounding box coordinates
    """
    height, width, _ = image.shape
    
    # Create a blob from the image
    blob = cv2.dnn.blobFromImage(image, 1/255, (416, 416), (0,0,0), True, crop=False)
    
    # Set input to the network
    net.setInput(blob)
    
    # Get output layer names
    output_layers = net.getUnconnectedOutLayersNames()
    
    # Forward pass
    outs = net.forward(output_layers)
    
    # Post-processing
    boxes = []
    confidences = []
    
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            
            if confidence > 0.5:  # Confidence threshold
                # Object detected
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                
                # Rectangle coordinates
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
    
    # Apply non-maximum suppression
    indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    
    if len(indices) > 0:
        idx = indices[0]
        box = boxes[idx]
        x, y, w, h = box
        
        # Ensure coordinates are within image bounds
        x = max(0, x)
        y = max(0, y)
        w = min(width - x, w)
        h = min(height - y, h)
        
        # Crop the plate from the image
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
