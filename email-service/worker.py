#!/usr/bin/env python3
# ===================================================================
# email-service/worker.py - Celery Worker for Email Service
# ===================================================================

import os
import sys
import signal
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import structlog
from celery import Celery
from celery.signals import worker_ready, worker_shutdown, task_prerun, task_postrun
from dotenv import load_dotenv

from config import EmailServiceConfig
from email_service import EmailService
from utils import EmailMetrics

# Load environment variables
load_dotenv()

# Configure logging
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

# Initialize configuration
config = EmailServiceConfig()

# Create Celery app
celery_app = Celery('email_worker')
celery_app.conf.update(config.get_celery_config())

# Global email service instance
email_service = None
email_metrics = None

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal"""
    global email_service, email_metrics
    
    logger.info("Email worker starting up", worker_id=sender.hostname if sender else 'unknown')
    
    try:
        # Initialize email service
        email_service = EmailService(config)
        
        # Initialize metrics
        email_metrics = EmailMetrics(email_service.redis_client)
        
        logger.info("Email worker ready", 
                   smtp_enabled=bool(email_service.smtp_client),
                   graph_enabled=bool(email_service.graph_client))
        
    except Exception as e:
        logger.error("Failed to initialize email worker", error=str(e))
        raise

@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown signal"""
    logger.info("Email worker shutting down", worker_id=sender.hostname if sender else 'unknown')

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task prerun signal"""
    logger.info("Starting email task", task_id=task_id, task_name=task.name if task else 'unknown')

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, 
                        retval=None, state=None, **kwds):
    """Handle task postrun signal"""
    logger.info("Completed email task", 
               task_id=task_id, 
               task_name=task.name if task else 'unknown',
               state=state)

# Email Tasks
@celery_app.task(name='send_email', bind=True, max_retries=3, default_retry_delay=300)
def send_email_task(self, email_data):
    """Send single email task"""
    try:
        start_time = time.time()
        
        # Validate email data
        if not email_data or not isinstance(email_data, dict):
            raise ValueError("Invalid email data")
        
        required_fields = ['to_email', 'subject', 'template_name']
        for field in required_fields:
            if field not in email_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Send email
        success = asyncio.run(email_service.send_email(email_data))
        
        # Record metrics
        duration_ms = (time.time() - start_time) * 1000
        template_name = email_data.get('template_name')
        
        if success:
            email_metrics.increment_sent_count(template_name)
            email_metrics.record_send_time(duration_ms, template_name)
            logger.info("Email sent successfully", 
                       to=email_data['to_email'],
                       template=template_name,
                       duration_ms=duration_ms)
        else:
            email_metrics.increment_failed_count(template_name, "send_failed")
            logger.error("Email sending failed", 
                        to=email_data['to_email'],
                        template=template_name)
        
        return {
            'success': success,
            'to_email': email_data['to_email'],
            'template_name': template_name,
            'duration_ms': duration_ms
        }
        
    except Exception as e:
        logger.error("Email task error", error=str(e), email_data=email_data)
        email_metrics.increment_failed_count(
            email_data.get('template_name'), 
            "task_error"
        )
        
        # Retry on certain errors
        if self.request.retries < self.max_retries:
            logger.info("Retrying email task", 
                       retry_count=self.request.retries + 1,
                       max_retries=self.max_retries)
            raise self.retry(countdown=self.default_retry_delay)
        
        return {
            'success': False,
            'error': str(e),
            'to_email': email_data.get('to_email', 'unknown'),
            'template_name': email_data.get('template_name', 'unknown')
        }

@celery_app.task(name='send_bulk_emails')
def send_bulk_emails_task(email_batch):
    """Send bulk emails task"""
    try:
        if not email_batch or not isinstance(email_batch, list):
            raise ValueError("Invalid email batch data")
        
        logger.info("Processing bulk emails", count=len(email_batch))
        
        results = asyncio.run(email_service.send_bulk_emails(email_batch))
        
        logger.info("Bulk emails processed", 
                   sent=results.get('sent', 0),
                   failed=results.get('failed', 0))
        
        return results
        
    except Exception as e:
        logger.error("Bulk email task error", error=str(e))
        return {
            'sent': 0,
            'failed': len(email_batch) if email_batch else 0,
            'errors': [str(e)]
        }

@celery_app.task(name='check_deadlines')
def check_deadlines_task():
    """Check deadlines and send notifications task"""
    try:
        logger.info("Checking deadlines for notifications")
        
        result = email_service.check_deadlines_and_notify()
        
        if 'error' in result:
            logger.error("Deadline check failed", error=result['error'])
        else:
            notifications_sent = result.get('notifications_sent', 0)
            logger.info("Deadline notifications processed", count=notifications_sent)
        
        return result
        
    except Exception as e:
        logger.error("Deadline check task error", error=str(e))
        return {'error': str(e)}

@celery_app.task(name='send_weekly_reports')
def send_weekly_reports_task():
    """Send weekly reports task"""
    try:
        logger.info("Generating and sending weekly reports")
        
        result = email_service.send_weekly_reports()
        
        if 'error' in result:
            logger.error("Weekly reports failed", error=result['error'])
        else:
            reports_sent = result.get('reports_sent', 0)
            logger.info("Weekly reports processed", count=reports_sent)
        
        return result
        
    except Exception as e:
        logger.error("Weekly reports task error", error=str(e))
        return {'error': str(e)}

@celery_app.task(name='send_daily_digest')
def send_daily_digest_task():
    """Send daily digest task"""
    try:
        logger.info("Generating and sending daily digest")
        
        # This would be implemented similar to weekly reports
        # but with daily statistics
        result = {'digest_sent': 0}  # Placeholder
        
        logger.info("Daily digest processed", count=result.get('digest_sent', 0))
        return result
        
    except Exception as e:
        logger.error("Daily digest task error", error=str(e))
        return {'error': str(e)}

@celery_app.task(name='cleanup_old_data')
def cleanup_old_data_task():
    """Cleanup old data task"""
    try:
        logger.info("Starting data cleanup")
        
        cleanup_count = 0
        
        # Cleanup old email logs
        try:
            redis_client = email_service.redis_client
            
            # Remove old email logs (keep last 30 days)
            cutoff_timestamp = (datetime.utcnow() - timedelta(days=30)).timestamp()
            
            # Cleanup send times
            removed = redis_client.zremrangebyscore('email_metrics:send_times', 0, cutoff_timestamp)
            cleanup_count += removed
            
            logger.info("Data cleanup completed", items_removed=cleanup_count)
            
        except Exception as e:
            logger.error("Data cleanup error", error=str(e))
        
        return {'cleanup_count': cleanup_count}
        
    except Exception as e:
        logger.error("Cleanup task error", error=str(e))
        return {'error': str(e)}

@celery_app.task(name='health_check')
def health_check_task():
    """Health check task"""
    try:
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'worker_id': celery_app.control.inspect().stats(),
            'email_service_status': 'healthy',
            'smtp_status': 'unknown',
            'graph_status': 'unknown',
            'database_status': 'unknown',
            'redis_status': 'unknown'
        }
        
        # Test SMTP connection
        if email_service.smtp_client:
            try:
                smtp_test = asyncio.run(email_service.smtp_client.test_connection())
                health_status['smtp_status'] = 'healthy' if smtp_test else 'unhealthy'
            except Exception:
                health_status['smtp_status'] = 'unhealthy'
        
        # Test Graph connection
        if email_service.graph_client:
            try:
                graph_test = asyncio.run(email_service.graph_client.test_connection())
                health_status['graph_status'] = 'healthy' if graph_test else 'unhealthy'
            except Exception:
                health_status['graph_status'] = 'unhealthy'
        
        # Test database connection
        try:
            with email_service.db_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            health_status['database_status'] = 'healthy'
        except Exception:
            health_status['database_status'] = 'unhealthy'
        
        # Test Redis connection
        try:
            email_service.redis_client.ping()
            health_status['redis_status'] = 'healthy'
        except Exception:
            health_status['redis_status'] = 'unhealthy'
        
        logger.info("Health check completed", status=health_status)
        return health_status
        
    except Exception as e:
        logger.error("Health check error", error=str(e))
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'email_service_status': 'unhealthy',
            'error': str(e)
        }

# Error handling
@celery_app.task(bind=True)
def error_handler(self, uuid):
    """Handle task errors"""
    result = self.app.AsyncResult(uuid)
    logger.error("Task failed", task_id=uuid, error=result.traceback)

# Monitoring tasks
@celery_app.task(name='generate_metrics_report')
def generate_metrics_report_task():
    """Generate metrics report"""
    try:
        metrics = email_metrics.get_metrics_summary()
        
        logger.info("Metrics report generated", metrics=metrics)
        return metrics
        
    except Exception as e:
        logger.error("Metrics report error", error=str(e))
        return {'error': str(e)}

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal", signal=signum)
    sys.exit(0)

def main():
    """Main worker entry point"""
    import time
    import asyncio
    from datetime import datetime, timedelta
    from sqlalchemy import text
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configure logging
    log_level = config.logging.level
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=config.logging.format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config.logging.file_path)
        ]
    )
    
    logger.info("Starting email worker", 
               environment=config.environment,
               log_level=log_level)
    
    try:
        # Start worker
        worker = celery_app.Worker(
            loglevel=log_level.lower(),
            traceback=True,
            concurrency=int(os.getenv('CELERY_CONCURRENCY', 2))
        )
        
        worker.start()
        
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error("Worker failed to start", error=str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()