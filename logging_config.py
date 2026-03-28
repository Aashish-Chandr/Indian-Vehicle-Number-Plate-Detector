import logging
import os
import sys

def setup_logging():
    """Configure logging for production and development."""
    log_level = logging.INFO if os.environ.get('FLASK_ENV') == 'production' else logging.DEBUG
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    return root_logger

# Configure on import
logger = setup_logging()
