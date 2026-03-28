import os
import logging
import kagglehub
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def download_kaggle_dataset(dataset_name="saisirishan/indian-vehicle-dataset", target_dir="dataset/kaggle_vehicles"):
    """
    Download a dataset from Kaggle and extract it to the target directory.
    
    Args:
        dataset_name (str): The name of the Kaggle dataset to download.
        target_dir (str): The target directory to extract the dataset to.
    
    Returns:
        str: Path to the extracted dataset
    """
    try:
        logger.info(f"Downloading Kaggle dataset: {dataset_name}")
        
        # Create the target directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)
        
        # Download the dataset
        path = kagglehub.dataset_download(dataset_name)
        logger.info(f"Dataset downloaded to: {path}")
        
        # Find all ZIP files in the downloaded path
        zip_files = list(Path(path).glob("**/*.zip"))
        
        if not zip_files:
            logger.warning("No ZIP files found in the downloaded dataset")
            return path
        
        # Extract each ZIP file to the target directory
        for zip_file in zip_files:
            logger.info(f"Extracting: {zip_file}")
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
        
        logger.info(f"Dataset extracted to: {target_dir}")
        return target_dir
        
    except Exception as e:
        logger.error(f"Error downloading Kaggle dataset: {str(e)}")
        raise

def organize_dataset_for_training(source_dir, target_dir="dataset/indian_plates_dataset"):
    """
    Organize the Kaggle dataset into the format required for training.
    The dataset should be organized with one folder per character (A-Z, 0-9).
    
    Args:
        source_dir (str): Source directory containing the downloaded dataset.
        target_dir (str): Target directory to organize the dataset for training.
    
    Returns:
        str: Path to the organized dataset directory
    """
    try:
        import cv2
        import numpy as np
        import xml.etree.ElementTree as ET
        from pathlib import Path
        import random
        
        # Create target directory for organized dataset
        os.makedirs(target_dir, exist_ok=True)
        
        # Create directories for each character (0-9, A-Z)
        for char in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            char_dir = os.path.join(target_dir, char)
            os.makedirs(char_dir, exist_ok=True)
        
        # List of dataset folders in the source directory
        dataset_folders = ['google_images', 'video_images', 'State-wise_OLX']
        
        # Process each dataset folder
        total_plates_processed = 0
        total_chars_extracted = 0
        
        for folder in dataset_folders:
            folder_path = os.path.join(source_dir, folder)
            
            if not os.path.exists(folder_path):
                logger.warning(f"Folder {folder_path} does not exist, skipping")
                continue
                
            logger.info(f"Processing {folder_path}")
            
            # Get all xml files
            xml_files = list(Path(folder_path).glob('**/*.xml'))
            logger.info(f"Found {len(xml_files)} XML files in {folder}")
            
            for xml_file in xml_files:
                try:
                    # Parse XML
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    
                    # Get image filename
                    filename = root.find('filename').text
                    img_path = os.path.join(os.path.dirname(xml_file), filename)
                    
                    # Check if image file exists (adjust path if needed)
                    if not os.path.exists(img_path):
                        alternative_img_path = str(xml_file).replace('.xml', '')
                        if os.path.exists(alternative_img_path):
                            img_path = alternative_img_path
                        else:
                            logger.warning(f"Image file not found for {xml_file}, skipping")
                            continue
                    
                    # Read image
                    img = cv2.imread(img_path)
                    if img is None:
                        logger.warning(f"Could not read image {img_path}, skipping")
                        continue
                    
                    # Get license plate number and bounding box
                    plate_obj = root.find('.//object')
                    if plate_obj is None:
                        continue
                        
                    # Get the license plate number
                    plate_number = plate_obj.find('n').text if plate_obj.find('n') is not None else None
                    
                    if not plate_number:
                        logger.warning(f"No license plate number found in {xml_file}, skipping")
                        continue
                    
                    # Clean the plate number
                    plate_number = ''.join(c for c in plate_number if c.isalnum())
                    
                    # Get bounding box
                    bbox = plate_obj.find('bndbox')
                    if bbox is None:
                        logger.warning(f"No bounding box found in {xml_file}, skipping")
                        continue
                        
                    xmin = int(bbox.find('xmin').text)
                    ymin = int(bbox.find('ymin').text)
                    xmax = int(bbox.find('xmax').text)
                    ymax = int(bbox.find('ymax').text)
                    
                    # Extract plate image
                    plate_img = img[ymin:ymax, xmin:xmax]
                    
                    # Process the license plate for individual characters
                    # We'll use a simple approach to divide the plate into equal segments based on the number of characters
                    
                    # Remove non-alphanumeric chars
                    plate_number = ''.join(c for c in plate_number if c.isalnum()).upper()
                    
                    if len(plate_number) > 0:
                        total_plates_processed += 1
                        
                        # Divide plate into segments for each character
                        plate_width = plate_img.shape[1]
                        segment_width = plate_width // len(plate_number)
                        
                        for i, char in enumerate(plate_number):
                            if char not in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                                continue
                                
                            # Extract character segment
                            start_x = i * segment_width
                            end_x = (i + 1) * segment_width if i < len(plate_number) - 1 else plate_width
                            
                            char_img = plate_img[:, start_x:end_x]
                            
                            # Add some randomization to the filename to avoid duplicates
                            random_id = random.randint(1000000, 9999999)
                            char_filename = f"{folder}_{total_plates_processed}_{i}_{random_id}.jpg"
                            
                            # Save character image
                            char_path = os.path.join(target_dir, char, char_filename)
                            cv2.imwrite(char_path, char_img)
                            total_chars_extracted += 1
                            
                except Exception as e:
                    logger.error(f"Error processing {xml_file}: {str(e)}")
                    continue
        
        logger.info(f"Processed {total_plates_processed} plates and extracted {total_chars_extracted} characters")
        logger.info(f"Dataset organized for training at: {target_dir}")
        return target_dir
        
    except Exception as e:
        logger.error(f"Error organizing dataset: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage
    download_path = download_kaggle_dataset()
    print(f"Dataset downloaded to: {download_path}")
