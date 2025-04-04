import os
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    """
    Check if the file has an allowed extension.
    
    Args:
        filename: The name of the file
        
    Returns:
        bool: True if the file extension is allowed, False otherwise
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_extension(filename):
    """
    Get the extension of a file.
    
    Args:
        filename: The name of the file
        
    Returns:
        str: The file extension
    """
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def create_directory_if_not_exists(directory_path):
    """
    Create a directory if it doesn't exist.
    
    Args:
        directory_path: Path to the directory to create
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        logger.debug(f"Created directory: {directory_path}")
