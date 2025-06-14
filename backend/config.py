# ===================================================================
# backend/config.py - Application Configuration
# ===================================================================

import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Basic Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://actionplan:secure_password@localhost:5432/actionplan'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_timeout': 30,
        'pool_recycle': 3600,
        'max_overflow': 30
    }
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET') or 'jwt-secret-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    
    # Microsoft 365 configuration
    MS_CLIENT_ID = os.environ.get('MS_CLIENT_ID')
    MS_CLIENT_SECRET = os.environ.get('MS_CLIENT_SECRET')
    MS_TENANT_ID = os.environ.get('MS_TENANT_ID')
    MS_AUTHORITY = f"https://login.microsoftonline.com/{MS_TENANT_ID}" if MS_TENANT_ID else None
    MS_SCOPE = ['User.Read', 'Files.ReadWrite.All']
    
    # OneDrive sync configuration
    ONEDRIVE_FOLDER_PATH = os.environ.get('ONEDRIVE_FOLDER_PATH', '/Action Plans')
    ONEDRIVE_FILE_NAME = os.environ.get('ONEDRIVE_FILE_NAME', 'Plan_daction.xlsx')
    SYNC_INTERVAL = int(os.environ.get('SYNC_INTERVAL', 300))  # 5 minutes
    
    # File upload configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    
    # Email configuration
    MAIL_SERVER = os.environ.get('SMTP_SERVER', 'smtp.office365.com')
    MAIL_PORT = int(os.environ.get('SMTP_PORT', 587))
    MAIL_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('SMTP_USER')
    MAIL_PASSWORD = os.environ.get('SMTP_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('EMAIL_FROM_ADDRESS', 'noreply@techmac.ma')
    
    # Redis configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    
    # Celery configuration
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    
    # Telegram Bot configuration
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_WEBHOOK_URL = os.environ.get('TELEGRAM_WEBHOOK_URL')
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Feature flags
    ENABLE_ONEDRIVE_SYNC = os.environ.get('ENABLE_ONEDRIVE_SYNC', 'true').lower() == 'true'
    ENABLE_EMAIL_NOTIFICATIONS = os.environ.get('ENABLE_EMAIL_NOTIFICATIONS', 'true').lower() == 'true'
    ENABLE_TELEGRAM_BOT = os.environ.get('ENABLE_TELEGRAM_BOT', 'false').lower() == 'true'
    
    # Security settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Backup configuration
    BACKUP_SCHEDULE = os.environ.get('BACKUP_SCHEDULE', '0 2 * * *')  # Daily at 2 AM
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    BACKUP_S3_BUCKET = os.environ.get('BACKUP_S3_BUCKET')
    
    # Notification settings
    DEADLINE_WARNING_DAYS = int(os.environ.get('DEADLINE_WARNING_DAYS', 3))
    OVERDUE_CHECK_INTERVAL = int(os.environ.get('OVERDUE_CHECK_INTERVAL', 3600))  # 1 hour

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration selection based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Get configuration class
def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])