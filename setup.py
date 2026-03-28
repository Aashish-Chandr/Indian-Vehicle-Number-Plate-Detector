from setuptools import setup, find_packages

setup(
    name="indian-vehicle-number-plate-detector",
    version="1.0.0",
    description="Indian Vehicle Number Plate Detection and OCR System",
    author="Aashish Chandr",
    python_requires=">=3.11",
    packages=find_packages(),
    install_requires=[
        "email-validator>=2.2.0",
        "flask>=3.1.0",
        "flask-sqlalchemy>=3.1.1",
        "gunicorn>=23.0.0",
        "kagglehub>=0.3.11",
        "numpy>=2.2.4",
        "openai>=1.70.0",
        "opencv-python>=4.11.0.86",
        "psycopg2-binary>=2.9.10",
        "pytesseract>=0.3.13",
        "python-levenshtein>=0.27.1",
        "scikit-learn>=1.6.1",
        "werkzeug>=3.1.3",
    ],
    entry_points={
        "console_scripts": [
            "run-app=app:main",
        ],
    },
)
