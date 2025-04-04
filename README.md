# Indian Vehicle Number Plate Detection

A web application that detects and recognizes Indian vehicle number plates from uploaded images.

## Features

- **Number Plate Detection**: Automatically detect vehicle license plates in uploaded images
- **OCR Recognition**: Extract text from the detected license plates
- **Multiple Plate Type Support**: Works with Indian, European, American, and other license plate formats
- **Download Results**: Save the detected plate images 
- **Model Training**: Train custom models to improve recognition for Indian license plates

## How It Works

1. **Upload**: Users upload an image containing a vehicle with a visible license plate
2. **Detection**: The application detects the license plate using computer vision techniques
3. **Recognition**: OCR is used to extract the text from the license plate
4. **Results**: The application displays the extracted text and allows downloading the plate image

## Training Custom Models

To improve recognition for Indian license plates, the application includes a training interface:

1. **Prepare Dataset**: Organize images by character (A-Z, 0-9) in folders
2. **Upload Dataset**: Zip the dataset and upload it through the training interface
3. **Train Model**: Start the training process to create a custom model
4. **Automatic Integration**: The trained model will be used automatically for future recognition

## Technologies Used

- **Backend**: Flask (Python)
- **Computer Vision**: OpenCV
- **OCR**: Tesseract
- **Machine Learning**: scikit-learn
- **Frontend**: HTML, CSS, JavaScript, Bootstrap

## Requirements

- Python 3.6+
- Flask
- OpenCV
- Tesseract OCR
- NumPy
- scikit-learn
