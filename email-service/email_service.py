#!/usr/bin/env python3
# ===================================================================
# email-service/email_service.py - Main Email Service Application
# ===================================================================

import os
import sys
import asyncio
import logging
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from celery import Celery
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import redis
from dotenv import load_dotenv

from smtp_client import SMTPClient
from templates import EmailTemplateManager
from microsoft_graph import GraphEmailClient

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

@dataclass
class EmailConfig:
    """Email service configuration"""
    smtp_server: str = os.getenv('SMTP_SERVER', 'smtp.office365.com')
    smtp_port: int = int(os.getenv('SMTP_PORT', 587))
    smtp_user: str = os.getenv('SMTP_USER', '')
    smtp_password: str = os.getenv('SMTP_PASSWORD', '')
    use_tls: bool = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
    from_address: str = os.getenv('EMAIL_FROM_ADDRESS', 'noreply@techmac.ma')
    from_name: str = os.getenv('EMAIL_FROM_NAME', 'Action Plan Management System')
    
    # Microsoft Graph API
    use_graph_api: bool = os.getenv('EMAIL_GRAPH_ENABLED', 'false').lower() == 'true'
    ms_client_id: str = os.getenv('MS_CLIENT_ID', '')
    ms_client_secret: str = os.getenv('MS_CLIENT_SECRET', '')
    ms_tenant_id: str = os.getenv('MS_TENANT_ID', '')
    
    # Database
    database_url: str = os.getenv('DATABASE_URL', 'postgresql://actionplan:password@db:5432/actionplan')
    
    # Redis
    redis_url: str = os.getenv('REDIS_URL', 'redis://cache:6379')
    
    # Notification settings
    deadline_warning_days: int = int(os.getenv('DEADLINE_WARNING_DAYS', 3))
    batch_size: int = int(os.getenv('EMAIL_BATCH_SIZE', 50))
    retry_count: int = int(os.getenv('EMAIL_RETRY_COUNT', 3))
    retry_delay: int = int(os.getenv('EMAIL_RETRY_DELAY', 300))  # 5 minutes

class EmailService:
    """Main Email Service Class"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.smtp_client = None
        self.graph_client = None
        self.template_manager = EmailTemplateManager()
        self.db_engine = None
        self.redis_client = None
        self.celery_app = None
        
        # Initialize components
        self._setup_database()
        self._setup_redis()
        self._setup_email_clients()
        self._setup_celery()
        
        logger.info("Email service initialized", 
                   smtp_enabled=bool(self.smtp_client),
                   graph_enabled=bool(self.graph_client))
    
    def _setup_database(self):
        """Setup database connection"""
        try:
            self.db_engine = create_engine(
                self.config.database_url,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600
            )
            
            # Test connection
            with self.db_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.SessionLocal = sessionmaker(bind=self.db_engine)
            logger.info("Database connection established")
            
        except Exception as e:
            logger.error("Failed to setup database", error=str(e))
            raise
    
    def _setup_redis(self):
        """Setup Redis connection"""
        try:
            self.redis_client = redis.from_url(
                self.config.redis_url,
                decode_responses=True,
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.error("Failed to setup Redis", error=str(e))
            raise
    
    def _setup_email_clients(self):
        """Setup email clients"""
        try:
            # Setup SMTP client
            if self.config.smtp_user and self.config.smtp_password:
                self.smtp_client = SMTPClient(
                    server=self.config.smtp_server,
                    port=self.config.smtp_port,
                    username=self.config.smtp_user,
                    password=self.config.smtp_password,
                    use_tls=self.config.use_tls,
                    from_address=self.config.from_address,
                    from_name=self.config.from_name
                )
                logger.info("SMTP client initialized")
            
            # Setup Microsoft Graph client
            if (self.config.use_graph_api and 
                self.config.ms_client_id and 
                self.config.ms_client_secret):
                
                self.graph_client = GraphEmailClient(
                    client_id=self.config.ms_client_id,
                    client_secret=self.config.ms_client_secret,
                    tenant_id=self.config.ms_tenant_id,
                    from_address=self.config.from_address,
                    from_name=self.config.from_name
                )
                logger.info("Microsoft Graph client initialized")
                
        except Exception as e:
            logger.error("Failed to setup email clients", error=str(e))
            # Don't raise - service can work without email clients
    
    def _setup_celery(self):
        """Setup Celery for background tasks"""
        try:
            self.celery_app = Celery(
                'email_service',
                broker=self.config.redis_url,
                backend=self.config.redis_url
            )
            
            self.celery_app.conf.update(
                task_serializer='json',
                accept_content=['json'],
                result_serializer='json',
                timezone='UTC',
                enable_utc=True,
                task_track_started=True,
                task_time_limit=300,  # 5 minutes
                task_soft_time_limit=240,  # 4 minutes
                worker_prefetch_multiplier=1,
                worker_max_tasks_per_child=1000,
            )
            
            # Register tasks
            self._register_celery_tasks()
            logger.info("Celery initialized")
            
        except Exception as e:
            logger.error("Failed to setup Celery", error=str(e))
            raise
    
    def _register_celery_tasks(self):
        """Register Celery tasks"""
        
        @self.celery_app.task(name='send_email', bind=True, max_retries=3)
        def send_email_task(self, email_data):
            """Celery task for sending emails"""
            try:
                return self.send_email(email_data)
            except Exception as e:
                logger.error("Email task failed", error=str(e), email_data=email_data)
                raise self.retry(countdown=self.config.retry_delay)
        
        @self.celery_app.task(name='send_bulk_emails')
        def send_bulk_emails_task(email_batch):
            """Celery task for sending bulk emails"""
            return self.send_bulk_emails(email_batch)
        
        @self.celery_app.task(name='check_deadlines')
        def check_deadlines_task():
            """Celery task for checking deadlines"""
            return self.check_deadlines_and_notify()
        
        @self.celery_app.task(name='send_weekly_reports')
        def send_weekly_reports_task():
            """Celery task for sending weekly reports"""
            return self.send_weekly_reports()
        
        # Store task references
        self.send_email_task = send_email_task
        self.send_bulk_emails_task = send_bulk_emails_task
        self.check_deadlines_task = check_deadlines_task
        self.send_weekly_reports_task = send_weekly_reports_task
    
    async def send_email(self, email_data: Dict) -> bool:
        """Send a single email"""
        try:
            # Validate email data
            required_fields = ['to_email', 'subject', 'template_name']
            for field in required_fields:
                if field not in email_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Generate email content
            html_content, text_content = self.template_manager.render_template(
                template_name=email_data['template_name'],
                context=email_data.get('context', {}),
                language=email_data.get('language', 'fr')
            )
            
            # Try Graph API first, then SMTP
            success = False
            
            if self.graph_client:
                try:
                    success = await self.graph_client.send_email(
                        to_email=email_data['to_email'],
                        subject=email_data['subject'],
                        html_content=html_content,
                        text_content=text_content,
                        attachments=email_data.get('attachments', [])
                    )
                    if success:
                        logger.info("Email sent via Graph API", to=email_data['to_email'])
                except Exception as e:
                    logger.warning("Graph API failed, trying SMTP", error=str(e))
            
            if not success and self.smtp_client:
                try:
                    success = await self.smtp_client.send_email(
                        to_email=email_data['to_email'],
                        subject=email_data['subject'],
                        html_content=html_content,
                        text_content=text_content,
                        attachments=email_data.get('attachments', [])
                    )
                    if success:
                        logger.info("Email sent via SMTP", to=email_data['to_email'])
                except Exception as e:
                    logger.error("SMTP failed", error=str(e))
            
            # Log result
            if success:
                self._log_email_sent(email_data)
            else:
                self._log_email_failed(email_data)
            
            return success
            
        except Exception as e:
            logger.error("Failed to send email", error=str(e), email_data=email_data)
            return False
    
    async def send_bulk_emails(self, emails: List[Dict]) -> Dict:
        """Send multiple emails in batches"""
        results = {
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        # Process in batches
        for i in range(0, len(emails), self.config.batch_size):
            batch = emails[i:i + self.config.batch_size]
            
            for email_data in batch:
                try:
                    success = await self.send_email(email_data)
                    if success:
                        results['sent'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"Failed to send to {email_data.get('to_email', 'unknown')}")
                        
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"Error sending to {email_data.get('to_email', 'unknown')}: {str(e)}")
            
            # Small delay between batches
            await asyncio.sleep(1)
        
        logger.info("Bulk email completed", **results)
        return results
    
    def check_deadlines_and_notify(self) -> Dict:
        """Check for approaching deadlines and send notifications"""
        try:
            with self.SessionLocal() as session:
                # Query for tasks with approaching deadlines
                warning_date = datetime.utcnow() + timedelta(days=self.config.deadline_warning_days)
                
                query = text("""
                    SELECT t.id, t.action_description, t.customer, t.responsible, 
                           t.deadline, u.email, u.name
                    FROM tasks t
                    LEFT JOIN users u ON u.name = t.responsible OR u.email LIKE '%' || t.responsible || '%'
                    WHERE t.deadline <= :warning_date 
                    AND t.deadline >= :today
                    AND t.status NOT IN ('Terminé', 'Annulé')
                """)
                
                results = session.execute(query, {
                    'warning_date': warning_date,
                    'today': datetime.utcnow()
                }).fetchall()
                
                notifications_sent = 0
                
                for row in results:
                    if row.email:
                        email_data = {
                            'to_email': row.email,
                            'subject': f'Rappel d\'échéance: {row.action_description[:50]}...',
                            'template_name': 'deadline_reminder',
                            'context': {
                                'user_name': row.name or row.responsible,
                                'task': {
                                    'id': row.id,
                                    'action_description': row.action_description,
                                    'customer': row.customer,
                                    'responsible': row.responsible,
                                    'deadline': row.deadline.strftime('%d/%m/%Y') if row.deadline else None,
                                },
                                'days_remaining': (row.deadline - datetime.utcnow().date()).days if row.deadline else 0
                            }
                        }
                        
                        # Queue email for sending
                        self.send_email_task.delay(email_data)
                        notifications_sent += 1
                
                logger.info("Deadline notifications queued", count=notifications_sent)
                return {'notifications_sent': notifications_sent}
                
        except Exception as e:
            logger.error("Failed to check deadlines", error=str(e))
            return {'error': str(e)}
    
    def send_weekly_reports(self) -> Dict:
        """Send weekly reports to managers and admins"""
        try:
            with self.SessionLocal() as session:
                # Get managers and admins
                query = text("""
                    SELECT email, name FROM users 
                    WHERE roles @> '["manager"]' OR roles @> '["admin"]'
                    AND is_active = true
                """)
                
                recipients = session.execute(query).fetchall()
                
                # Get weekly statistics
                week_start = datetime.utcnow() - timedelta(days=7)
                
                stats_query = text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE created_at >= :week_start) as tasks_created,
                        COUNT(*) FILTER (WHERE updated_at >= :week_start AND status = 'Terminé') as tasks_completed,
                        COUNT(*) FILTER (WHERE deadline < :today AND status NOT IN ('Terminé', 'Annulé')) as tasks_overdue
                    FROM tasks
                """)
                
                stats = session.execute(stats_query, {
                    'week_start': week_start,
                    'today': datetime.utcnow()
                }).fetchone()
                
                reports_sent = 0
                
                for recipient in recipients:
                    email_data = {
                        'to_email': recipient.email,
                        'subject': f'Rapport Hebdomadaire - Semaine du {week_start.strftime("%d/%m/%Y")}',
                        'template_name': 'weekly_report',
                        'context': {
                            'user_name': recipient.name,
                            'week_start': week_start.strftime('%d/%m/%Y'),
                            'stats': {
                                'tasks_created': stats.tasks_created,
                                'tasks_completed': stats.tasks_completed,
                                'tasks_overdue': stats.tasks_overdue
                            }
                        }
                    }
                    
                    # Queue email for sending
                    self.send_email_task.delay(email_data)
                    reports_sent += 1
                
                logger.info("Weekly reports queued", count=reports_sent)
                return {'reports_sent': reports_sent}
                
        except Exception as e:
            logger.error("Failed to send weekly reports", error=str(e))
            return {'error': str(e)}
    
    def _log_email_sent(self, email_data: Dict):
        """Log successful email sending"""
        try:
            log_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'to_email': email_data['to_email'],
                'subject': email_data['subject'],
                'template': email_data.get('template_name'),
                'status': 'sent'
            }
            
            # Store in Redis for monitoring
            self.redis_client.lpush('email_log', str(log_data))
            self.redis_client.ltrim('email_log', 0, 999)  # Keep last 1000 logs
            
        except Exception as e:
            logger.error("Failed to log email sent", error=str(e))
    
    def _log_email_failed(self, email_data: Dict):
        """Log failed email sending"""
        try:
            log_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'to_email': email_data['to_email'],
                'subject': email_data['subject'],
                'template': email_data.get('template_name'),
                'status': 'failed'
            }
            
            # Store in Redis for monitoring
            self.redis_client.lpush('email_failures', str(log_data))
            self.redis_client.ltrim('email_failures', 0, 999)  # Keep last 1000 failures
            
        except Exception as e:
            logger.error("Failed to log email failure", error=str(e))
    
    async def run_worker(self):
        """Run the Celery worker"""
        try:
            logger.info("Starting email service worker")
            
            # Start Celery worker
            worker = self.celery_app.Worker(
                loglevel='INFO',
                traceback=True,
                concurrency=2
            )
            
            worker.start()
            
        except Exception as e:
            logger.error("Worker failed", error=str(e))
            raise
    
    def get_stats(self) -> Dict:
        """Get email service statistics"""
        try:
            stats = {
                'sent_count': self.redis_client.llen('email_log'),
                'failed_count': self.redis_client.llen('email_failures'),
                'smtp_enabled': bool(self.smtp_client),
                'graph_enabled': bool(self.graph_client),
                'last_check': datetime.utcnow().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get stats", error=str(e))
            return {'error': str(e)}

def setup_periodic_tasks(email_service):
    """Setup periodic tasks"""
    
    # Check deadlines every hour
    email_service.celery_app.conf.beat_schedule = {
        'check-deadlines': {
            'task': 'check_deadlines',
            'schedule': 3600.0,  # Every hour
        },
        'send-weekly-reports': {
            'task': 'send_weekly_reports',
            'schedule': 604800.0,  # Every week
        },
    }
    
    email_service.celery_app.conf.timezone = 'UTC'

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal", signal=sig)
    sys.exit(0)

async def main():
    """Main application entry point"""
    try:
        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Initialize email service
        config = EmailConfig()
        email_service = EmailService(config)
        
        # Setup periodic tasks
        setup_periodic_tasks(email_service)
        
        logger.info("Email service starting")
        
        # Run the worker
        await email_service.run_worker()
        
    except Exception as e:
        logger.error("Email service failed to start", error=str(e))
        sys.exit(1)

if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/email_service.log')
        ]
    )
    
    # Run the service
    asyncio.run(main())