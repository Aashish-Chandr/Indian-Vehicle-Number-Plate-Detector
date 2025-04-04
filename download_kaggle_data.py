"""
Utility script to download and test the Kaggle dataset functionality.
"""

import os
import logging
from kaggle_dataset_loader import download_kaggle_dataset, organize_dataset_for_training

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to download and organize dataset."""
    # Set dataset name and target directory
    dataset_name = "saisirishan/indian-vehicle-dataset"
    target_dir = os.path.join(os.getcwd(), 'dataset', 'kaggle_test')
    
    try:
        # Download dataset
        logger.info(f"Downloading dataset {dataset_name} to {target_dir}")
        download_path = download_kaggle_dataset(dataset_name, target_dir)
        
        logger.info(f"Dataset downloaded to: {download_path}")
        
        # Organize dataset for training
        organized_path = organize_dataset_for_training(download_path)
        
        logger.info(f"Dataset organized for training at: {organized_path}")
        logger.info("Download and organization complete!")
        
    except Exception as e:
        logger.error(f"Error downloading or organizing dataset: {str(e)}")

if __name__ == "__main__":
    main()