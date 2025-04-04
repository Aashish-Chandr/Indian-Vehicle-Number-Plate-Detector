import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import uuid
import cv2
import numpy as np
from werkzeug.utils import secure_filename
import tempfile
import shutil
from number_plate_detector import detect_number_plate
from ocr_reader import extract_text_from_plate
from utils import allowed_file, get_file_extension, create_directory_if_not_exists
import model_trainer

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Configure upload folder
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'uploads')
DETECTION_FOLDER = os.path.join(tempfile.gettempdir(), 'detections')
create_directory_if_not_exists(UPLOAD_FOLDER)
create_directory_if_not_exists(DETECTION_FOLDER)

# Maximum allowed filesize (5MB)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DETECTION_FOLDER'] = DETECTION_FOLDER

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Process uploaded image file.
    - Save the uploaded image
    - Detect number plate
    - Perform OCR to extract text
    - Return results
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get plate type (default to Indian)
    plate_type = request.form.get('plate_type', 'indian')
    
    if file and allowed_file(file.filename):
        try:
            # Generate unique filenames
            original_filename = secure_filename(file.filename)
            extension = get_file_extension(original_filename)
            
            unique_id = str(uuid.uuid4())
            original_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}.{extension}")
            plate_path = os.path.join(app.config['DETECTION_FOLDER'], f"{unique_id}_plate.{extension}")
            
            # Save uploaded file
            file.save(original_path)
            logger.debug(f"Saved original image to {original_path}")
            
            # Process with OpenCV
            image = cv2.imread(original_path)
            if image is None:
                return jsonify({'error': 'Unable to read image'}), 400
            
            # Detect number plate
            plate_image, plate_bbox = detect_number_plate(image)
            
            if plate_image is None:
                return jsonify({'error': 'No number plate detected in the image'}), 400
            
            # Save the detected plate image
            cv2.imwrite(plate_path, plate_image)
            logger.debug(f"Saved plate image to {plate_path}")
            
            # Extract text from number plate using OCR
            plate_text = extract_text_from_plate(plate_image, plate_type=plate_type)
            
            # Annotate the original image with bounding box
            annotated_image = image.copy()
            x, y, w, h = plate_bbox
            cv2.rectangle(annotated_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Add text label above the bounding box
            label = plate_text if plate_text else "Unknown"
            cv2.putText(annotated_image, label, (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            # Save the annotated image
            annotated_path = os.path.join(app.config['DETECTION_FOLDER'], f"{unique_id}_annotated.{extension}")
            cv2.imwrite(annotated_path, annotated_image)
            
            # Return results
            result = {
                'original_image': f"/get_image?path={original_path}&type=original",
                'plate_image': f"/get_image?path={plate_path}&type=plate",
                'annotated_image': f"/get_image?path={annotated_path}&type=annotated",
                'plate_text': plate_text,
                'plate_type': plate_type,
                'download_url': f"/download?path={plate_path}",
                'download_annotated_url': f"/download?path={annotated_path}",
                'success': True
            }
            
            # Add confidence metric if available
            if hasattr(plate_text, 'confidence'):
                result['confidence'] = plate_text.confidence
                
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return jsonify({'error': f'Error processing image: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type. Please upload a JPG or PNG image'}), 400

@app.route('/get_image')
def get_image():
    """Serve image files."""
    path = request.args.get('path')
    image_type = request.args.get('type')
    
    if not path:
        return "Image not found", 404
    
    try:
        return send_file(path, mimetype=f'image/{get_file_extension(path)}')
    except Exception as e:
        logger.error(f"Error serving image: {str(e)}")
        return "Error serving image", 500

@app.route('/download')
def download_plate():
    """Allow downloading the detected plate image."""
    path = request.args.get('path')
    
    if not path:
        return "Image not found", 404
    
    try:
        filename = f"number_plate.{get_file_extension(path)}"
        return send_file(path, 
                         mimetype=f'image/{get_file_extension(path)}',
                         as_attachment=True,
                         download_name=filename)
    except Exception as e:
        logger.error(f"Error downloading image: {str(e)}")
        return "Error downloading image", 500

# Configure dataset folder
DATASET_FOLDER = os.path.join(os.getcwd(), 'dataset')
create_directory_if_not_exists(DATASET_FOLDER)
app.config['DATASET_FOLDER'] = DATASET_FOLDER

@app.route('/train')
def train_page():
    """Render the training page."""
    return render_template('train.html')
    
@app.route('/test_ind_plate')
def test_ind_plate():
    """Test the IND plate detection with a sample image."""
    try:
        # Path to the test image
        test_image_path = 'static/temp_test_plate.jpg'
        
        # Read the image
        image = cv2.imread(test_image_path)
        if image is None:
            return jsonify({'error': 'Could not read test image'}), 400
            
        # Detect plate
        plate_image, plate_bbox = detect_number_plate(image)
        
        if plate_image is None:
            return jsonify({'error': 'No license plate detected in the image'}), 400
            
        # Save detected plate
        detection_id = str(uuid.uuid4())
        plate_path = os.path.join(app.config['DETECTION_FOLDER'], f'plate_{detection_id}.jpg')
        cv2.imwrite(plate_path, plate_image)
        
        # Extract text from the plate image
        plate_text = extract_text_from_plate(plate_image, 'indian')
        
        # Return results
        return jsonify({
            'success': True,
            'message': 'License plate detected and processed successfully',
            'plate_text': plate_text,
            'plate_image': f'/get_image?path={plate_path}',
            'download_url': f'/download_plate?id={detection_id}'
        })
    except Exception as e:
        logger.error(f"Error in test_ind_plate: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload_dataset', methods=['POST'])
def upload_dataset():
    """
    Process uploaded dataset.
    - Save the dataset
    - Organize it for training
    - Return results
    """
    if 'dataset_zip' not in request.files:
        return jsonify({'error': 'No dataset file uploaded'}), 400
    
    file = request.files['dataset_zip']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check file type (accept only zip files)
    if not file.filename.endswith('.zip'):
        return jsonify({'error': 'Please upload a ZIP file containing the dataset'}), 400
    
    try:
        # Generate unique dataset ID
        dataset_id = str(uuid.uuid4())
        dataset_path = os.path.join(app.config['DATASET_FOLDER'], dataset_id)
        os.makedirs(dataset_path, exist_ok=True)
        
        # Save uploaded zip file
        zip_path = os.path.join(dataset_path, 'dataset.zip')
        file.save(zip_path)
        logger.debug(f"Saved dataset zip to {zip_path}")
        
        # Extract the zip file
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dataset_path)
        
        logger.debug(f"Extracted dataset to {dataset_path}")
        
        # Return success
        return jsonify({
            'success': True,
            'dataset_id': dataset_id,
            'message': 'Dataset uploaded successfully and is ready for training.'
        })
        
    except Exception as e:
        logger.error(f"Error processing dataset: {str(e)}")
        return jsonify({'error': f'Error processing dataset: {str(e)}'}), 500

@app.route('/start_training', methods=['POST'])
def start_training():
    """
    Start the model training process.
    """
    try:
        # Get dataset ID from request
        dataset_id = request.form.get('dataset_id')
        if not dataset_id:
            return jsonify({'error': 'No dataset ID provided'}), 400
        
        # Check if dataset exists
        dataset_path = os.path.join(app.config['DATASET_FOLDER'], dataset_id)
        if not os.path.exists(dataset_path):
            return jsonify({'error': 'Dataset not found'}), 404
        
        # Get model type from request (default to random_forest)
        model_type = request.form.get('model_type', 'random_forest')
        
        # Start training
        success = model_trainer.run_model_training(dataset_path)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Model training completed successfully. The model is now ready for use.'
            })
        else:
            return jsonify({
                'error': 'Model training failed. Please check the dataset format and try again.'
            }), 500
            
    except Exception as e:
        logger.error(f"Error training model: {str(e)}")
        return jsonify({'error': f'Error training model: {str(e)}'}), 500

@app.route('/get_training_status')
def get_training_status():
    """
    Check if a trained model exists.
    """
    model_path = model_trainer.DEFAULT_MODEL_PATH
    status = os.path.exists(model_path)
    
    return jsonify({
        'model_exists': status,
        'model_path': model_path if status else None
    })

@app.route('/download_kaggle_dataset', methods=['POST'])
def download_kaggle_dataset():
    """
    Download dataset from Kaggle for training.
    """
    try:
        # Import here to avoid loading unnecessary dependencies at startup
        from kaggle_dataset_loader import download_kaggle_dataset
        
        dataset_name = request.form.get('dataset_name', 'saisirishan/indian-vehicle-dataset')
        target_dir = os.path.join(app.config['DATASET_FOLDER'], 'kaggle_vehicles')
        
        # Create a unique ID for this download
        dataset_id = str(uuid.uuid4())
        target_dir = os.path.join(app.config['DATASET_FOLDER'], dataset_id)
        
        # Download the dataset
        logger.info(f"Starting Kaggle dataset download: {dataset_name}")
        download_path = download_kaggle_dataset(dataset_name, target_dir)
        logger.info(f"Kaggle dataset downloaded to: {download_path}")
        
        return jsonify({
            'success': True,
            'dataset_id': dataset_id,
            'dataset_path': download_path,
            'message': 'Dataset downloaded successfully and is ready for training.'
        })
    except Exception as e:
        logger.error(f"Error downloading Kaggle dataset: {str(e)}")
        return jsonify({'error': f'Error downloading dataset: {str(e)}'}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
