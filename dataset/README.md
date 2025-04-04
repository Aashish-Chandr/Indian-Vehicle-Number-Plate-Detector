# Training Dataset for Indian License Plate Recognition

This directory is for training the license plate recognition model. To get the best results, the dataset should follow a specific structure:

## Dataset Structure

```
dataset/
├── your_dataset_name/
│   ├── 0/
│   │   ├── image1.jpg
│   │   ├── image2.jpg
│   │   └── ...
│   ├── 1/
│   │   ├── image1.jpg
│   │   ├── image2.jpg
│   │   └── ...
│   ├── A/
│   │   ├── image1.jpg
│   │   ├── image2.jpg
│   │   └── ...
│   ├── B/
│   │   └── ...
│   └── ...
```

- Each folder should be named after the character it represents (A, B, C, ..., 0, 1, 2, ...)
- Inside each folder, place images of the corresponding characters from Indian license plates
- The images should contain a single character, ideally cropped closely around the character
- Supported formats: JPG, PNG

## How to Train

1. Upload a ZIP file containing your dataset through the training page
2. The dataset will be automatically extracted and processed
3. Click "Train Model" to start the training process
4. Once training is complete, the model will be automatically saved and used for recognition

## Sample Dataset

A sample directory structure has been created at `dataset/indian_plates_example/` to show how the dataset should be organized.

## Tips for Better Results

- Include a variety of samples for each character with different lighting, angles, and fonts
- For best results, aim for at least 50-100 images per character
- Include images with slight noise, shadows, and variations to make the model more robust
- The characters should be properly segmented and cropped
- If you have more data for some characters than others, the model might be biased - try to balance the dataset

## Preprocessing

The training process will automatically preprocess images to enhance features and extract relevant information for model training. You don't need to preprocess the images yourself, but providing clean and well-cropped character images will yield better results.
