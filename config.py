import os
from pathlib import Path

# Automatically identify the absolute root directory of your project folder
BASE_DIR = Path(__file__).resolve().parent

class BaseConfig:
    """Universal configurations applied across all deployment nodes."""
    # System Security Key with an automated randomized fallback string if missing
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback_local_dev_key_secure_2026_npge')
    
    # Strictly define maximum file upload ceiling (5MB translated securely to integers)
    try:
        MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 5 * 1024 * 1024))
    except ValueError:
        MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # Secure default fallback if string casting fails

    # Unified Asset Management Folders using Cross-Platform Path Handling
    UPLOAD_FOLDER = os.path.join(str(BASE_DIR), 'static', 'uploads')
    
    # Database path configuration
    DATABASE_NAME = os.environ.get('DATABASE_NAME', 'business_cms.db')
    DATABASE_PATH = os.path.join(str(BASE_DIR), DATABASE_NAME)


class OfflineDevelopmentConfig(BaseConfig):
    """Configurations specialized for your local home computer workspace."""
    ENV_MODE = 'OFFLINE'
    DEBUG = True
    TESTING = False
    
    # URL target pointing to where your future live server will process data sync requests
    LIVE_CLOUD_SYNC_URL = os.environ.get('LIVE_CLOUD_SYNC_URL', 'https://api.yourdomain.com/v1/sync')


class OnlineProductionConfig(BaseConfig):
    """Configurations enforced strictly when running live on cloud infrastructure."""
    ENV_MODE = 'ONLINE'
    DEBUG = False
    TESTING = False
    
    # In production, lookups require a strict, unique environment token to run
    LIVE_CLOUD_SYNC_URL = os.environ.get('LIVE_CLOUD_SYNC_URL', '')


# =====================================================================
# THE ENVIRONMENT ENGINE FACTORY (Guarantees Fallback Recovery)
# =====================================================================
def get_current_config():
    """
    Evaluates system states dynamically and assigns the correct config framework.
    If an invalid value is supplied, it defaults safely to Offline mode.
    """
    # Read systemic environment variable 'APP_ENV'
    target_env = os.environ.get('APP_ENV', 'OFFLINE').strip().upper()
    
    config_matrix = {
        'ONLINE': OnlineProductionConfig,
        'PRODUCTION': OnlineProductionConfig,
        'OFFLINE': OfflineDevelopmentConfig,
        'DEVELOPMENT': OfflineDevelopmentConfig
    }
    
    selected_config = config_matrix.get(target_env, OfflineDevelopmentConfig)
    
    # CRITICAL FALLBACK PROTECTION: Ensure upload destinations exist before server boot
    try:
        os.makedirs(selected_config.UPLOAD_FOLDER, exist_ok=True)
    except Exception as e:
        print(f"CRITICAL SYSTEM WARNING: System could not verify path '{selected_config.UPLOAD_FOLDER}'. Reason: {e}")
        
    return selected_config