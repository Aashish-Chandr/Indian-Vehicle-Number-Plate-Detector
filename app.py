import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
import uuid
import cv2
import numpy as np
from werkzeug.utils import secure_filename
import tempfile
from number_plate_detector import detect_number_plate
from ocr_reader import extract_text_from_plate
from utils import allowed_file, get_file_extension, create_directory_if_not_exists

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
            plate_text = extract_text_from_plate(plate_image)
            
            # Return results
            return jsonify({
                'original_image': f"/get_image?path={original_path}&type=original",
                'plate_image': f"/get_image?path={plate_path}&type=plate",
                'plate_text': plate_text,
                'download_url': f"/download?path={plate_path}",
                'success': True
            })
            
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
