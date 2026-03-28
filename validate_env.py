import os
import logging

logger = logging.getLogger(__name__)

def validate_environment():
    """Validate all required environment variables and system dependencies."""
    
    errors = []
    warnings = []
    
    # Check Flask environment
    flask_env = os.environ.get('FLASK_ENV', 'development')
    logger.info(f"FLASK_ENV: {flask_env}")
    
    # Check Session Secret
    session_secret = os.environ.get('SESSION_SECRET')
    if not session_secret or session_secret == 'dev-secret-key-change-in-production':
        if flask_env == 'production':
            errors.append("SESSION_SECRET not properly set in production")
        else:
            warnings.append("Using development SESSION_SECRET")
    
    # Check Python unbuffered
    pythonunbuffered = os.environ.get('PYTHONUNBUFFERED', '0')
    if pythonunbuffered != '1':
        warnings.append("PYTHONUNBUFFERED is not set to 1 (recommended for streaming logs)")
    
    # Check temp directories exist
    import tempfile
    temp_dir = tempfile.gettempdir()
    if not os.path.exists(temp_dir):
        errors.append(f"Temp directory not accessible: {temp_dir}")
    
    # Check models directory
    models_dir = os.path.join(os.path.dirname(__file__), 'models')
    if not os.path.exists(models_dir):
        os.makedirs(models_dir, exist_ok=True)
        logger.info(f"Created models directory: {models_dir}")
    
    # Check templates directory
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        errors.append(f"Templates directory not found: {templates_dir}")
    
    # Check static directory
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir, exist_ok=True)
        logger.info(f"Created static directory: {static_dir}")
    
    # Log warnings
    for warning in warnings:
        logger.warning(f"⚠️  {warning}")
    
    # Log errors and raise if critical
    for error in errors:
        logger.error(f"❌ {error}")
    
    if errors:
        raise RuntimeError(f"Environment validation failed with {len(errors)} error(s)")
    
    logger.info("✓ Environment validation passed")
    return True

if __name__ == '__main__':
    validate_environment()
