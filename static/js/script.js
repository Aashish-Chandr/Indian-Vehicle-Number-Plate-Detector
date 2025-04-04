document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const filePreviewContainer = document.getElementById('file-preview-container');
    const filePreview = document.getElementById('file-preview');
    const uploadContainer = document.getElementById('upload-container');
    const changeImageBtn = document.getElementById('change-image-btn');
    const processImageBtn = document.getElementById('process-image-btn');
    const loadingContainer = document.getElementById('loading-container');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    const resultsContainer = document.getElementById('results-container');
    const originalImage = document.getElementById('original-image');
    const plateImage = document.getElementById('plate-image');
    const plateText = document.getElementById('plate-text');
    const plateTypeDisplay = document.getElementById('plate-type-display');
    const downloadPlateBtn = document.getElementById('download-plate-btn');
    const tryAgainBtn = document.getElementById('try-again-btn');
    
    // Event Listeners
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop area when dragging over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);
    
    // Handle file selection via click
    dropArea.addEventListener('click', () => {
        fileInput.click();
    });
    
    fileInput.addEventListener('change', handleFileSelect);
    
    // Button event listeners
    changeImageBtn.addEventListener('click', resetUpload);
    processImageBtn.addEventListener('click', processImage);
    tryAgainBtn.addEventListener('click', resetApp);
    
    // Helper Functions
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight() {
        dropArea.classList.add('highlight');
    }
    
    function unhighlight() {
        dropArea.classList.remove('highlight');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length) {
            handleFiles(files);
        }
    }
    
    function handleFileSelect(e) {
        const files = e.target.files;
        
        if (files.length) {
            handleFiles(files);
        }
    }
    
    function handleFiles(files) {
        const file = files[0];
        
        if (!isValidFileType(file)) {
            showError("Invalid file type. Please upload a JPG or PNG image.");
            return;
        }
        
        if (!isValidFileSize(file)) {
            showError("File is too large. Maximum size is 5MB.");
            return;
        }
        
        // Preview the file
        previewFile(file);
        
        // Hide error if it was shown
        hideError();
    }
    
    function isValidFileType(file) {
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
        return validTypes.includes(file.type);
    }
    
    function isValidFileSize(file) {
        const maxSize = 5 * 1024 * 1024; // 5MB
        return file.size <= maxSize;
    }
    
    function previewFile(file) {
        const reader = new FileReader();
        
        reader.onloadend = function() {
            filePreview.src = reader.result;
            dropArea.classList.add('d-none');
            filePreviewContainer.classList.remove('d-none');
        };
        
        if (file) {
            reader.readAsDataURL(file);
        }
    }
    
    function resetUpload() {
        fileInput.value = '';
        filePreview.src = '';
        filePreviewContainer.classList.add('d-none');
        dropArea.classList.remove('d-none');
    }
    
    function processImage() {
        if (!fileInput.files.length) {
            showError("Please select an image first.");
            return;
        }
        
        // Show loading indicator
        loadingContainer.classList.remove('d-none');
        
        // Hide error if it was shown
        hideError();
        
        // Get selected plate type
        const plateTypeSelect = document.getElementById('plate-type-select');
        const plateType = plateTypeSelect.value;
        
        // Update loading text based on plate type
        const loadingText = document.querySelector('.loading-text');
        if (loadingText) {
            loadingText.textContent = `Detecting ${plateType.charAt(0).toUpperCase() + plateType.slice(1)} Number Plate...`;
        }
        
        // Create form data to send to server
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('plate_type', plateType);
        
        // Send to server
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || 'Server error');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                displayResults(data);
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError(error.message || 'Failed to process image. Please try again.');
        })
        .finally(() => {
            // Hide loading indicator
            loadingContainer.classList.add('d-none');
        });
    }
    
    function displayResults(data) {
        // Set image sources
        originalImage.src = data.original_image;
        plateImage.src = data.plate_image;
        
        // Set plate text
        plateText.textContent = data.plate_text || 'No text detected';
        
        // Set plate type
        if (plateTypeDisplay) {
            // Format plate type for display (capitalize first letter)
            const formattedType = data.plate_type.charAt(0).toUpperCase() + data.plate_type.slice(1);
            plateTypeDisplay.textContent = formattedType;
        }
        
        // Set download link
        downloadPlateBtn.href = data.download_url;
        
        // Hide upload container
        uploadContainer.classList.add('d-none');
        
        // Show results container
        resultsContainer.classList.remove('d-none');
    }
    
    function resetApp() {
        // Reset file input
        fileInput.value = '';
        
        // Hide results
        resultsContainer.classList.add('d-none');
        
        // Reset upload container
        filePreviewContainer.classList.add('d-none');
        dropArea.classList.remove('d-none');
        uploadContainer.classList.remove('d-none');
        
        // Clear images
        filePreview.src = '';
        originalImage.src = '';
        plateImage.src = '';
        
        // Clear plate text
        plateText.textContent = '';
        if (plateTypeDisplay) {
            plateTypeDisplay.textContent = '';
        }
    }
    
    function showError(message) {
        errorMessage.textContent = message;
        errorContainer.classList.remove('d-none');
        
        // Hide loading if it's shown
        loadingContainer.classList.add('d-none');
    }
    
    function hideError() {
        errorContainer.classList.add('d-none');
    }
});
