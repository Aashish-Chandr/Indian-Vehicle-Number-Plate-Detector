import os
import cv2
import numpy as np
import logging
import pickle
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn import metrics
import joblib
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
MODEL_DIR = 'models'
DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, 'indian_plate_classifier.pkl')

# Ensure model directory exists
Path(MODEL_DIR).mkdir(parents=True, exist_ok=True)

def preprocess_image_for_training(image):
    """
    Preprocess image for training - convert to standard size and extract features
    
    Args:
        image: OpenCV image
        
    Returns:
        features: Extracted feature vector
    """
    # Resize to standard size
    std_size = (100, 32)  # Width, Height - typical aspect ratio for license plates
    
    try:
        # Convert to grayscale if it's a color image
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Resize image to standard size for consistent feature extraction
        resized = cv2.resize(gray, std_size, interpolation=cv2.INTER_AREA)
        
        # Normalize pixel values
        normalized = resized / 255.0
        
        # Apply binary threshold
        _, binary = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Feature extraction
        features = []
        
        # 1. Add flattened raw pixels as features
        features.extend(normalized.flatten())
        
        # 2. Add histogram of oriented gradients (simple version)
        # Calculate gradients
        gx = cv2.Sobel(normalized, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(normalized, cv2.CV_32F, 0, 1, ksize=3)
        
        # Calculate gradient magnitude and direction
        magnitude, angle = cv2.cartToPolar(gx, gy, angleInDegrees=True)
        
        # Create a histogram of gradient directions
        hist_bins = 9  # Number of bins
        hist_range = (0, 180)  # Angle range
        hist = cv2.calcHist([angle.astype(np.float32)], [0], None, [hist_bins], hist_range)
        hist = cv2.normalize(hist, hist).flatten()
        features.extend(hist)
        
        # 3. Add horizontal and vertical projections
        h_projection = np.sum(binary, axis=1) / binary.shape[1]
        v_projection = np.sum(binary, axis=0) / binary.shape[0]
        features.extend(h_projection)
        features.extend(v_projection)
        
        return np.array(features, dtype=np.float32)
    
    except Exception as e:
        logger.error(f"Error preprocessing image for training: {str(e)}")
        return None

def load_dataset(data_folder, limit=None):
    """
    Load and preprocess dataset for training
    
    Args:
        data_folder: Path to dataset folder
        limit: Optional limit on number of images to process
        
    Returns:
        features: Array of feature vectors
        labels: Array of labels
    """
    features = []
    labels = []
    
    logger.info(f"Loading dataset from {data_folder}")
    
    # Check if the directory exists
    if not os.path.isdir(data_folder):
        logger.error(f"Dataset directory {data_folder} does not exist")
        return None, None
    
    # Check structure - expect one subdirectory per license plate character
    subdirs = [d for d in os.listdir(data_folder) if os.path.isdir(os.path.join(data_folder, d))]
    
    if not subdirs:
        logger.error(f"No subdirectories found in {data_folder}. Expected one directory per character class.")
        return None, None
    
    # Process each subdirectory as a character class
    count = 0
    for char_class in subdirs:
        char_path = os.path.join(data_folder, char_class)
        logger.debug(f"Processing class: {char_class}")
        
        # Get all image files in the directory
        img_files = [f for f in os.listdir(char_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        logger.debug(f"Found {len(img_files)} images for class {char_class}")
        
        # Process each image
        for img_file in img_files:
            try:
                img_path = os.path.join(char_path, img_file)
                img = cv2.imread(img_path)
                
                if img is None:
                    logger.warning(f"Failed to load image: {img_path}")
                    continue
                
                # Extract features
                feature_vector = preprocess_image_for_training(img)
                
                if feature_vector is not None:
                    features.append(feature_vector)
                    labels.append(char_class)
                    count += 1
                    
                    if limit and count >= limit:
                        logger.info(f"Reached limit of {limit} images")
                        break
                    
            except Exception as e:
                logger.error(f"Error processing image {img_file}: {str(e)}")
        
        if limit and count >= limit:
            break
    
    logger.info(f"Processed {count} images from {len(subdirs)} character classes")
    
    if not features:
        logger.error("No features extracted from dataset")
        return None, None
    
    return np.array(features), np.array(labels)

def train_model(features, labels, model_type='random_forest'):
    """
    Train a model on the provided features and labels
    
    Args:
        features: Array of feature vectors
        labels: Array of labels
        model_type: Type of model to train ('random_forest', 'svm', 'knn')
        
    Returns:
        model: Trained model
        label_encoder: Fitted label encoder
    """
    logger.info(f"Training {model_type} model on {len(features)} samples")
    
    # Encode labels
    label_encoder = LabelEncoder()
    encoded_labels = label_encoder.fit_transform(labels)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        features, encoded_labels, test_size=0.2, random_state=42
    )
    
    # Select model
    if model_type == 'svm':
        model = SVC(probability=True)
    elif model_type == 'knn':
        model = KNeighborsClassifier(n_neighbors=5)
    else:  # default to random forest
        model = RandomForestClassifier(n_estimators=100, random_state=42)
    
    # Train model
    logger.debug(f"Training model on {len(X_train)} samples")
    model.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test)
    accuracy = metrics.accuracy_score(y_test, y_pred)
    logger.info(f"Model accuracy: {accuracy:.4f}")
    
    # Print classification report
    logger.info("\nClassification Report:")
    logger.info(metrics.classification_report(y_test, y_pred))
    
    return model, label_encoder

def save_model(model, label_encoder, model_path=DEFAULT_MODEL_PATH):
    """
    Save the trained model and label encoder
    
    Args:
        model: Trained model
        label_encoder: Fitted label encoder
        model_path: Path to save the model
        
    Returns:
        success: Boolean indicating success
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Save as pickle with both model and encoder
        with open(model_path, 'wb') as f:
            pickle.dump({'model': model, 'encoder': label_encoder}, f)
        
        logger.info(f"Model saved to {model_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving model: {str(e)}")
        return False

def load_trained_model(model_path=DEFAULT_MODEL_PATH):
    """
    Load the trained model and label encoder
    
    Args:
        model_path: Path to the saved model
        
    Returns:
        model: Loaded model
        label_encoder: Loaded label encoder
    """
    try:
        if not os.path.exists(model_path):
            logger.error(f"Model file {model_path} not found")
            return None, None
        
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        
        model = data['model']
        label_encoder = data['encoder']
        
        logger.info(f"Model loaded from {model_path}")
        logger.debug(f"Model can predict {len(label_encoder.classes_)} classes: {label_encoder.classes_}")
        
        return model, label_encoder
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        return None, None

def train_from_folder(data_folder, model_type='random_forest', model_path=DEFAULT_MODEL_PATH):
    """
    Train a model from a dataset folder and save it
    
    Args:
        data_folder: Path to dataset folder
        model_type: Type of model to train
        model_path: Path to save the model
        
    Returns:
        success: Boolean indicating success
    """
    # Load and preprocess dataset
    features, labels = load_dataset(data_folder)
    
    if features is None or labels is None:
        logger.error("Failed to load dataset")
        return False
    
    # Train model
    model, label_encoder = train_model(features, labels, model_type)
    
    # Save model
    return save_model(model, label_encoder, model_path)

def run_model_training(data_path):
    """
    Run the training process for the Indian license plate model
    
    Args:
        data_path: Path to the dataset
        
    Returns:
        success: Boolean indicating success
    """
    logger.info("Starting model training for Indian license plates")
    
    if not os.path.exists(data_path):
        logger.error(f"Dataset path {data_path} does not exist")
        return False
    
    result = train_from_folder(data_path)
    
    if result:
        logger.info("Model training completed successfully")
    else:
        logger.error("Model training failed")
    
    return result

if __name__ == "__main__":
    # Example usage
    data_path = "dataset/indian_plates"
    run_model_training(data_path)