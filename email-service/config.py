# ===================================================================
# email-service/config.py - Email Service Configuration
# ===================================================================

import os
from typing import Optional, List
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class SMTPConfig:
    """SMTP Configuration"""
    server: str = os.getenv('SMTP_SERVER', 'smtp.office365.com')
    port: int = int(os.getenv('SMTP_PORT', 587))
    username: str = os.getenv('SMTP_USER', '')
    password: str = os.getenv('SMTP_PASSWORD', '')
    use_tls: bool = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
    timeout: int = int(os.getenv('SMTP_TIMEOUT', 30))

@dataclass
class GraphConfig:
    """Microsoft Graph Configuration"""
    enabled: bool = os.getenv('EMAIL_GRAPH_ENABLED', 'false').lower() == 'true'
    client_id: str = os.getenv('MS_CLIENT_ID', '')
    client_secret: str = os.getenv('MS_CLIENT_SECRET', '')
    tenant_id: str = os.getenv('MS_TENANT_ID', '')
    authority: str = os.getenv('MS_AUTHORITY', f"https://login.microsoftonline.com/{os.getenv('MS_TENANT_ID', '')}")
    scopes: List[str] = field(default_factory=lambda: ['https://graph.microsoft.com/.default'])

@dataclass
class DatabaseConfig:
    """Database Configuration"""
    url: str = os.getenv('DATABASE_URL', 'postgresql://actionplan:password@db:5432/actionplan')
    pool_size: int = int(os.getenv('DB_POOL_SIZE', 10))
    max_overflow: int = int(os.getenv('DB_MAX_OVERFLOW', 20))
    pool_timeout: int = int(os.getenv('DB_POOL_TIMEOUT', 30))
    pool_recycle: int = int(os.getenv('DB_POOL_RECYCLE', 3600))

@dataclass
class RedisConfig:
    """Redis Configuration"""
    url: str = os.getenv('REDIS_URL', 'redis://cache:6379')
    password: Optional[str] = os.getenv('REDIS_PASSWORD')
    decode_responses: bool = True
    health_check_interval: int = int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', 30))
    socket_keepalive: bool = True
    socket_keepalive_options: dict = field(default_factory=lambda: {})

@dataclass
class CeleryConfig:
    """Celery Configuration"""
    broker_url: str = os.getenv('REDIS_URL', 'redis://cache:6379')
    result_backend: str = os.getenv('REDIS_URL', 'redis://cache:6379')
    task_serializer: str = 'json'
    accept_content: List[str] = field(default_factory=lambda: ['json'])
    result_serializer: str = 'json'
    timezone: str = os.getenv('TZ', 'UTC')
    enable_utc: bool = True
    task_track_started: bool = True
    task_time_limit: int = int(os.getenv('EMAIL_TASK_TIME_LIMIT', 300))  # 5 minutes
    task_soft_time_limit: int = int(os.getenv('EMAIL_TASK_SOFT_TIME_LIMIT', 240))  # 4 minutes
    worker_prefetch_multiplier: int = int(os.getenv('CELERY_PREFETCH_MULTIPLIER', 1))
    worker_max_tasks_per_child: int = int(os.getenv('CELERY_MAX_TASKS_PER_CHILD', 1000))

@dataclass
class EmailSettings:
    """Email Settings"""
    from_address: str = os.getenv('EMAIL_FROM_ADDRESS', 'noreply@techmac.ma')
    from_name: str = os.getenv('EMAIL_FROM_NAME', 'Action Plan Management System')
    reply_to: Optional[str] = os.getenv('EMAIL_REPLY_TO')
    support_email: str = os.getenv('SUPPORT_EMAIL', 'support@techmac.ma')
    
    # Template settings
    default_language: str = os.getenv('DEFAULT_LANGUAGE', 'fr')
    template_dir: str = os.getenv('EMAIL_TEMPLATE_DIR', 'templates')
    
    # Notification settings
    deadline_warning_days: int = int(os.getenv('DEADLINE_WARNING_DAYS', 3))
    batch_size: int = int(os.getenv('EMAIL_BATCH_SIZE', 50))
    retry_count: int = int(os.getenv('EMAIL_RETRY_COUNT', 3))
    retry_delay: int = int(os.getenv('EMAIL_RETRY_DELAY', 300))  # 5 minutes
    
    # Rate limiting
    rate_limit_per_minute: int = int(os.getenv('EMAIL_RATE_LIMIT_PER_MINUTE', 100))
    rate_limit_burst: int = int(os.getenv('EMAIL_RATE_LIMIT_BURST', 20))
    
    # Content settings
    max_subject_length: int = int(os.getenv('EMAIL_MAX_SUBJECT_LENGTH', 200))
    max_content_length: int = int(os.getenv('EMAIL_MAX_CONTENT_LENGTH', 1000000))  # 1MB
    allowed_attachment_types: List[str] = field(default_factory=lambda: 
        os.getenv('EMAIL_ALLOWED_ATTACHMENT_TYPES', 'pdf,doc,docx,xlsx,csv,png,jpg,jpeg').split(','))
    max_attachment_size: int = int(os.getenv('EMAIL_MAX_ATTACHMENT_SIZE', 10485760))  # 10MB

@dataclass
class NotificationConfig:
    """Notification Configuration"""
    # Feature flags
    email_enabled: bool = os.getenv('NOTIFICATION_EMAIL_ENABLED', 'true').lower() == 'true'
    telegram_enabled: bool = os.getenv('NOTIFICATION_TELEGRAM_ENABLED', 'false').lower() == 'true'
    browser_enabled: bool = os.getenv('NOTIFICATION_BROWSER_ENABLED', 'true').lower() == 'true'
    
    # Trigger settings
    notify_on_task_created: bool = os.getenv('NOTIFY_ON_TASK_CREATED', 'true').lower() == 'true'
    notify_on_task_completed: bool = os.getenv('NOTIFY_ON_TASK_COMPLETED', 'true').lower() == 'true'
    notify_on_deadline_approaching: bool = os.getenv('NOTIFY_ON_DEADLINE_APPROACHING', 'true').lower() == 'true'
    notify_on_overdue_tasks: bool = os.getenv('NOTIFY_ON_OVERDUE_TASKS', 'true').lower() == 'true'
    notify_on_task_updated: bool = os.getenv('NOTIFY_ON_TASK_UPDATED', 'false').lower() == 'true'
    notify_on_task_assigned: bool = os.getenv('NOTIFY_ON_TASK_ASSIGNED', 'true').lower() == 'true'
    
    # Scheduling
    deadline_check_interval: int = int(os.getenv('DEADLINE_CHECK_INTERVAL', 3600))  # 1 hour
    overdue_check_interval: int = int(os.getenv('OVERDUE_CHECK_INTERVAL', 3600))  # 1 hour
    weekly_report_day: int = int(os.getenv('WEEKLY_REPORT_DAY', 1))  # Monday = 1
    weekly_report_hour: int = int(os.getenv('WEEKLY_REPORT_HOUR', 8))  # 8 AM
    
    # Digest settings
    daily_digest_enabled: bool = os.getenv('DAILY_DIGEST_ENABLED', 'false').lower() == 'true'
    daily_digest_hour: int = int(os.getenv('DAILY_DIGEST_HOUR', 9))  # 9 AM
    weekly_digest_enabled: bool = os.getenv('WEEKLY_DIGEST_ENABLED', 'true').lower() == 'true'

@dataclass
class LoggingConfig:
    """Logging Configuration"""
    level: str = os.getenv('LOG_LEVEL', 'INFO')
    format: str = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_path: str = os.getenv('EMAIL_LOG_FILE', 'logs/email_service.log')
    max_bytes: int = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10MB
    backup_count: int = int(os.getenv('LOG_BACKUP_COUNT', 5))
    
    # Structured logging
    structured_logging: bool = os.getenv('STRUCTURED_LOGGING', 'true').lower() == 'true'
    log_to_console: bool = os.getenv('LOG_TO_CONSOLE', 'true').lower() == 'true'
    log_to_file: bool = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'

@dataclass
class SecurityConfig:
    """Security Configuration"""
    # Rate limiting
    enable_rate_limiting: bool = os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
    rate_limit_storage: str = os.getenv('RATE_LIMIT_STORAGE', 'redis')
    
    # Content security
    enable_content_filtering: bool = os.getenv('ENABLE_CONTENT_FILTERING', 'true').lower() == 'true'
    max_recipients_per_email: int = int(os.getenv('MAX_RECIPIENTS_PER_EMAIL', 100))
    
    # Encryption
    encrypt_sensitive_data: bool = os.getenv('ENCRYPT_SENSITIVE_DATA', 'true').lower() == 'true'
    encryption_key: Optional[str] = os.getenv('ENCRYPTION_KEY')
    
    # Authentication
    require_authentication: bool = os.getenv('EMAIL_REQUIRE_AUTH', 'true').lower() == 'true'
    allowed_domains: List[str] = field(default_factory=lambda: 
        os.getenv('EMAIL_ALLOWED_DOMAINS', '').split(',') if os.getenv('EMAIL_ALLOWED_DOMAINS') else [])
    
    # Anti-spam
    enable_spam_detection: bool = os.getenv('ENABLE_SPAM_DETECTION', 'false').lower() == 'true'
    spam_threshold: float = float(os.getenv('SPAM_THRESHOLD', 0.7))

@dataclass
class MonitoringConfig:
    """Monitoring Configuration"""
    # Metrics
    enable_metrics: bool = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
    metrics_port: int = int(os.getenv('METRICS_PORT', 8000))
    metrics_path: str = os.getenv('METRICS_PATH', '/metrics')
    
    # Health checks
    health_check_endpoint: str = os.getenv('HEALTH_CHECK_ENDPOINT', '/health')
    health_check_interval: int = int(os.getenv('HEALTH_CHECK_INTERVAL', 30))
    
    # Alerting
    enable_alerting: bool = os.getenv('ENABLE_ALERTING', 'false').lower() == 'true'
    alert_webhook_url: Optional[str] = os.getenv('ALERT_WEBHOOK_URL')
    
    # Performance monitoring
    track_performance: bool = os.getenv('TRACK_PERFORMANCE', 'true').lower() == 'true'
    slow_query_threshold: float = float(os.getenv('SLOW_QUERY_THRESHOLD', 1.0))  # seconds

@dataclass
class DevelopmentConfig:
    """Development Configuration"""
    debug: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    testing: bool = os.getenv('TESTING', 'false').lower() == 'true'
    mock_email_sending: bool = os.getenv('MOCK_EMAIL_SENDING', 'false').lower() == 'true'
    email_debug_recipient: Optional[str] = os.getenv('EMAIL_DEBUG_RECIPIENT')
    save_email_to_file: bool = os.getenv('SAVE_EMAIL_TO_FILE', 'false').lower() == 'true'
    email_file_path: str = os.getenv('EMAIL_FILE_PATH', 'debug_emails/')

@dataclass
class EmailServiceConfig:
    """Main Email Service Configuration"""
    # Core configurations
    smtp: SMTPConfig = field(default_factory=SMTPConfig)
    graph: GraphConfig = field(default_factory=GraphConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    celery: CeleryConfig = field(default_factory=CeleryConfig)
    
    # Service configurations
    email: EmailSettings = field(default_factory=EmailSettings)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    development: DevelopmentConfig = field(default_factory=DevelopmentConfig)
    
    # Application settings
    app_name: str = os.getenv('APP_NAME', 'Email Service')
    app_version: str = os.getenv('APP_VERSION', '1.0.0')
    environment: str = os.getenv('ENVIRONMENT', 'development')
    
    # Frontend settings
    frontend_url: str = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    api_url: str = os.getenv('API_URL', 'http://localhost:5000')
    
    # Company information
    company_name: str = os.getenv('COMPANY_NAME', 'TechMac')
    company_domain: str = os.getenv('COMPANY_DOMAIN', 'techmac.ma')
    company_address: str = os.getenv('COMPANY_ADDRESS', '')
    company_phone: str = os.getenv('COMPANY_PHONE', '')
    
    def __post_init__(self):
        """Post-initialization validation"""
        self._validate_configuration()
        self._setup_derived_settings()
    
    def _validate_configuration(self):
        """Validate configuration settings"""
        errors = []
        
        # Validate SMTP configuration if not using Graph
        if not self.graph.enabled:
            if not self.smtp.username or not self.smtp.password:
                errors.append("SMTP username and password are required when Graph API is disabled")
            if not self.smtp.server:
                errors.append("SMTP server is required")
        
        # Validate Graph configuration if enabled
        if self.graph.enabled:
            if not all([self.graph.client_id, self.graph.client_secret, self.graph.tenant_id]):
                errors.append("Microsoft Graph client_id, client_secret, and tenant_id are required when Graph API is enabled")
        
        # Validate database URL
        if not self.database.url:
            errors.append("Database URL is required")
        
        # Validate Redis URL
        if not self.redis.url:
            errors.append("Redis URL is required")
        
        # Validate email settings
        if not self.email.from_address:
            errors.append("From email address is required")
        
        # Validate security settings
        if self.security.encrypt_sensitive_data and not self.security.encryption_key:
            errors.append("Encryption key is required when encryption is enabled")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def _setup_derived_settings(self):
        """Setup derived settings based on configuration"""
        # Setup Redis password if provided
        if self.redis.password:
            if '?' in self.redis.url:
                self.redis.url += f"&password={self.redis.password}"
            else:
                self.redis.url += f"?password={self.redis.password}"
        
        # Setup logging directory
        import os
        from pathlib import Path
        log_dir = Path(self.logging.file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup debug email directory
        if self.development.save_email_to_file:
            debug_dir = Path(self.development.email_file_path)
            debug_dir.mkdir(parents=True, exist_ok=True)
    
    def get_template_context(self) -> dict:
        """Get default template context"""
        return {
            'company_name': self.company_name,
            'system_name': self.email.from_name,
            'base_url': self.frontend_url,
            'api_url': self.api_url,
            'support_email': self.email.support_email,
            'company_domain': self.company_domain,
            'company_address': self.company_address,
            'company_phone': self.company_phone,
            'current_year': str(datetime.now().year),
            'environment': self.environment
        }
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() == 'development'
    
    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.development.testing
    
    @classmethod
    def from_env_file(cls, env_file: str = '.env') -> 'EmailServiceConfig':
        """Create configuration from environment file"""
        from dotenv import load_dotenv
        load_dotenv(env_file)
        return cls()
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        import dataclasses
        return dataclasses.asdict(self)
    
    def get_celery_config(self) -> dict:
        """Get Celery configuration dictionary"""
        return {
            'broker_url': self.celery.broker_url,
            'result_backend': self.celery.result_backend,
            'task_serializer': self.celery.task_serializer,
            'accept_content': self.celery.accept_content,
            'result_serializer': self.celery.result_serializer,
            'timezone': self.celery.timezone,
            'enable_utc': self.celery.enable_utc,
            'task_track_started': self.celery.task_track_started,
            'task_time_limit': self.celery.task_time_limit,
            'task_soft_time_limit': self.celery.task_soft_time_limit,
            'worker_prefetch_multiplier': self.celery.worker_prefetch_multiplier,
            'worker_max_tasks_per_child': self.celery.worker_max_tasks_per_child,
            'beat_schedule': self._get_beat_schedule()
        }
    
    def _get_beat_schedule(self) -> dict:
        """Get Celery beat schedule"""
        schedule = {}
        
        if self.notifications.notify_on_deadline_approaching:
            schedule['check-deadlines'] = {
                'task': 'email_service.check_deadlines',
                'schedule': self.notifications.deadline_check_interval,
            }
        
        if self.notifications.notify_on_overdue_tasks:
            schedule['check-overdue'] = {
                'task': 'email_service.check_overdue_tasks',
                'schedule': self.notifications.overdue_check_interval,
            }
        
        if self.notifications.weekly_digest_enabled:
            schedule['weekly-report'] = {
                'task': 'email_service.send_weekly_reports',
                'schedule': crontab(
                    day_of_week=self.notifications.weekly_report_day,
                    hour=self.notifications.weekly_report_hour,
                    minute=0
                ),
            }
        
        if self.notifications.daily_digest_enabled:
            schedule['daily-digest'] = {
                'task': 'email_service.send_daily_digest',
                'schedule': crontab(
                    hour=self.notifications.daily_digest_hour,
                    minute=0
                ),
            }
        
        return schedule

# Helper functions
def get_config() -> EmailServiceConfig:
    """Get email service configuration"""
    return EmailServiceConfig()

def validate_email_address(email: str) -> bool:
    """Validate email address format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
    return re.match(pattern, email) is not None

def get_environment() -> str:
    """Get current environment"""
    return os.getenv('ENVIRONMENT', 'development').lower()

def is_production() -> bool:
    """Check if running in production"""
    return get_environment() == 'production'

def is_development() -> bool:
    """Check if running in development"""
    return get_environment() == 'development'

# Import required modules for crontab
try:
    from celery.schedules import crontab
    from datetime import datetime
except ImportError:
    # Fallback if celery is not installed
    def crontab(*args, **kwargs):
        return None
    
    from datetime import datetime