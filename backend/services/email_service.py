#!/usr/bin/env python3
# ===================================================================
# backend/services/email_service.py - Complete Email Service
# ===================================================================

import os
import logging
import smtplib
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from jinja2 import Environment, FileSystemLoader, select_autoescape
import redis
from celery import Celery
from flask import current_app, render_template_string
import threading
from dataclasses import dataclass, asdict
from enum import Enum

from app.models import EmailLog, Task, User, EmailTemplate, EmailQueue
from app import db

logger = logging.getLogger(__name__)

class EmailPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class EmailStatus(Enum):
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"
    DELIVERED = "delivered"

@dataclass
class EmailMessage:
    to: Union[str, List[str]]
    subject: str
    template: str
    context: Dict[str, Any]
    from_email: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    attachments: Optional[List[Dict]] = None
    priority: EmailPriority = EmailPriority.NORMAL
    send_at: Optional[datetime] = None
    user_id: Optional[str] = None
    task_id: Optional[str] = None
    email_type: str = "notification"

class EmailTemplateEngine:
    """Enhanced template engine for email rendering"""
    
    def __init__(self):
        self.template_dir = current_app.config.get('EMAIL_TEMPLATE_DIR', 'email-service/templates')
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        self.env.filters['datetime_format'] = self._datetime_format
        self.env.filters['currency'] = self._currency_format
        self.env.filters['truncate_words'] = self._truncate_words
        
    def _datetime_format(self, value: datetime, format_string: str = '%d/%m/%Y %H:%M') -> str:
        """Format datetime for display"""
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value.strftime(format_string)
        
    def _currency_format(self, value: float, currency: str = 'MAD') -> str:
        """Format currency values"""
        return f"{value:,.2f} {currency}"
        
    def _truncate_words(self, text: str, length: int = 50) -> str:
        """Truncate text to specified word count"""
        words = str(text).split()
        if len(words) <= length:
            return text
        return ' '.join(words[:length]) + '...'
        
    def render_template(self, template_name: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Render email template with context"""
        try:
            # Load template
            template = self.env.get_template(template_name)
            
            # Add common context variables
            enhanced_context = {
                **context,
                'current_date': datetime.now(),
                'app_name': current_app.config.get('APP_NAME', 'Action Plan Manager'),
                'company_name': current_app.config.get('COMPANY_NAME', 'TechMac'),
                'support_email': current_app.config.get('SUPPORT_EMAIL', 'support@techmac.ma'),
                'app_url': current_app.config.get('APP_URL', 'http://localhost:3000')
            }
            
            # Render template
            content = template.render(**enhanced_context)
            
            # Split HTML and text versions if template supports it
            if '<!-- TEXT_VERSION -->' in content:
                parts = content.split('<!-- TEXT_VERSION -->')
                return {
                    'html': parts[0].strip(),
                    'text': parts[1].strip() if len(parts) > 1 else None
                }
            else:
                return {
                    'html': content,
                    'text': None
                }
                
        except Exception as e:
            logger.error(f"Template rendering error: {str(e)}")
            raise Exception(f"Failed to render template {template_name}: {str(e)}")

class EmailDeliveryService:
    """Handle email delivery with multiple providers and retry logic"""
    
    def __init__(self):
        self.smtp_config = {
            'server': current_app.config.get('SMTP_SERVER', 'smtp.office365.com'),
            'port': int(current_app.config.get('SMTP_PORT', 587)),
            'username': current_app.config.get('SMTP_USER'),
            'password': current_app.config.get('SMTP_PASSWORD'),
            'use_tls': current_app.config.get('SMTP_USE_TLS', True),
            'use_ssl': current_app.config.get('SMTP_USE_SSL', False)
        }
        
        self.default_from = current_app.config.get('DEFAULT_FROM_EMAIL', 'noreply@techmac.ma')
        self.max_retries = int(current_app.config.get('EMAIL_MAX_RETRIES', 3))
        self.retry_delay = int(current_app.config.get('EMAIL_RETRY_DELAY', 300))  # 5 minutes
        
    def send_email(self, message: EmailMessage) -> Dict[str, Any]:
        """Send email with retry logic and error handling"""
        start_time = datetime.utcnow()
        
        try:
            # Validate message
            self._validate_message(message)
            
            # Create MIME message
            mime_msg = self._create_mime_message(message)
            
            # Send via SMTP
            result = self._send_via_smtp(mime_msg, message)
            
            # Log successful delivery
            self._log_email(message, 'sent', None, start_time)
            
            return {
                'success': True,
                'message_id': result.get('message_id'),
                'sent_at': datetime.utcnow()
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Email delivery failed: {error_msg}")
            
            # Log failed delivery
            self._log_email(message, 'failed', error_msg, start_time)
            
            return {
                'success': False,
                'error': error_msg,
                'failed_at': datetime.utcnow()
            }
            
    def _validate_message(self, message: EmailMessage) -> None:
        """Validate email message"""
        if not message.to:
            raise ValueError("Recipient email is required")
            
        if not message.subject:
            raise ValueError("Email subject is required")
            
        if not message.template and not message.context.get('content'):
            raise ValueError("Email template or content is required")
            
        # Validate email addresses
        recipients = message.to if isinstance(message.to, list) else [message.to]
        for email in recipients:
            if not self._is_valid_email(email):
                raise ValueError(f"Invalid email address: {email}")
                
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
        return re.match(pattern, email) is not None
        
    def _create_mime_message(self, message: EmailMessage) -> MIMEMultipart:
        """Create MIME message from EmailMessage"""
        # Create message container
        mime_msg = MIMEMultipart('alternative')
        
        # Set headers
        mime_msg['From'] = message.from_email or self.default_from
        mime_msg['Subject'] = message.subject
        
        # Handle recipients
        if isinstance(message.to, list):
            mime_msg['To'] = ', '.join(message.to)
        else:
            mime_msg['To'] = message.to
            
        if message.cc:
            mime_msg['Cc'] = ', '.join(message.cc)
            
        # Set priority
        if message.priority == EmailPriority.HIGH:
            mime_msg['X-Priority'] = '2'
            mime_msg['Importance'] = 'High'
        elif message.priority == EmailPriority.URGENT:
            mime_msg['X-Priority'] = '1'
            mime_msg['Importance'] = 'High'
            
        # Add message ID for tracking
        message_id = f"<{hashlib.md5(f'{message.subject}{datetime.utcnow().isoformat()}'.encode()).hexdigest()}@techmac.ma>"
        mime_msg['Message-ID'] = message_id
        
        # Render content
        template_engine = EmailTemplateEngine()
        
        if message.template:
            rendered = template_engine.render_template(message.template, message.context)
            
            # Add text version if available
            if rendered.get('text'):
                text_part = MIMEText(rendered['text'], 'plain', 'utf-8')
                mime_msg.attach(text_part)
                
            # Add HTML version
            if rendered.get('html'):
                html_part = MIMEText(rendered['html'], 'html', 'utf-8')
                mime_msg.attach(html_part)
        else:
            # Use direct content
            content = message.context.get('content', '')
            text_part = MIMEText(content, 'plain', 'utf-8')
            mime_msg.attach(text_part)
            
        # Add attachments
        if message.attachments:
            for attachment in message.attachments:
                self._add_attachment(mime_msg, attachment)
                
        return mime_msg
        
    def _add_attachment(self, mime_msg: MIMEMultipart, attachment: Dict) -> None:
        """Add attachment to MIME message"""
        try:
            file_path = attachment.get('path')
            filename = attachment.get('filename') or os.path.basename(file_path)
            
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            
            mime_msg.attach(part)
            
        except Exception as e:
            logger.warning(f"Failed to add attachment {attachment}: {str(e)}")
            
    def _send_via_smtp(self, mime_msg: MIMEMultipart, message: EmailMessage) -> Dict[str, Any]:
        """Send email via SMTP"""
        try:
            # Create SMTP connection
            if self.smtp_config['use_ssl']:
                server = smtplib.SMTP_SSL(self.smtp_config['server'], self.smtp_config['port'])
            else:
                server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
                if self.smtp_config['use_tls']:
                    server.starttls()
                    
            # Login
            if self.smtp_config['username'] and self.smtp_config['password']:
                server.login(self.smtp_config['username'], self.smtp_config['password'])
                
            # Send message
            recipients = []
            if isinstance(message.to, list):
                recipients.extend(message.to)
            else:
                recipients.append(message.to)
                
            if message.cc:
                recipients.extend(message.cc)
            if message.bcc:
                recipients.extend(message.bcc)
                
            server.send_message(mime_msg, to_addrs=recipients)
            server.quit()
            
            return {
                'message_id': mime_msg['Message-ID'],
                'recipients': recipients
            }
            
        except Exception as e:
            raise Exception(f"SMTP delivery failed: {str(e)}")
            
    def _log_email(self, message: EmailMessage, status: str, error: Optional[str], start_time: datetime) -> None:
        """Log email delivery attempt"""
        try:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            email_log = EmailLog(
                to_email=message.to if isinstance(message.to, str) else ', '.join(message.to),
                subject=message.subject,
                template=message.template,
                status=status,
                error_message=error,
                user_id=message.user_id,
                task_id=message.task_id,
                email_type=message.email_type,
                sent_at=datetime.utcnow() if status == 'sent' else None,
                duration_seconds=duration
            )
            
            db.session.add(email_log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to log email: {str(e)}")

class EmailQueueManager:
    """Manage email queue with Redis backend"""
    
    def __init__(self):
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = redis.from_url(redis_url)
        self.queue_key = 'email_queue'
        self.processing_key = 'email_processing'
        self.failed_key = 'email_failed'
        
    def add_to_queue(self, message: EmailMessage) -> str:
        """Add email message to queue"""
        try:
            # Generate unique ID
            message_id = hashlib.md5(
                f"{message.to}{message.subject}{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()
            
            # Serialize message
            message_data = {
                'id': message_id,
                'message': asdict(message),
                'created_at': datetime.utcnow().isoformat(),
                'attempts': 0,
                'max_attempts': 3
            }
            
            # Add to appropriate queue based on priority and send_at
            if message.send_at and message.send_at > datetime.utcnow():
                # Schedule for later
                score = message.send_at.timestamp()
                self.redis_client.zadd(f"{self.queue_key}:scheduled", {json.dumps(message_data): score})
            else:
                # Add to immediate queue based on priority
                priority_score = message.priority.value
                self.redis_client.zadd(self.queue_key, {json.dumps(message_data): priority_score})
                
            logger.info(f"Added email to queue: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to add email to queue: {str(e)}")
            raise
            
    def get_next_message(self) -> Optional[Dict]:
        """Get next message from queue"""
        try:
            # First check scheduled messages
            now = datetime.utcnow().timestamp()
            scheduled = self.redis_client.zrangebyscore(
                f"{self.queue_key}:scheduled", 
                0, 
                now, 
                start=0, 
                num=1,
                withscores=True
            )
            
            if scheduled:
                message_data, score = scheduled[0]
                self.redis_client.zrem(f"{self.queue_key}:scheduled", message_data)
                return json.loads(message_data)
                
            # Get highest priority message from main queue
            result = self.redis_client.zpopmax(self.queue_key)
            if result:
                message_data, priority = result
                return json.loads(message_data)
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get next message: {str(e)}")
            return None
            
    def mark_processing(self, message_data: Dict) -> None:
        """Mark message as being processed"""
        try:
            processing_data = {
                **message_data,
                'processing_started': datetime.utcnow().isoformat()
            }
            
            self.redis_client.setex(
                f"{self.processing_key}:{message_data['id']}", 
                300,  # 5 minutes timeout
                json.dumps(processing_data)
            )
            
        except Exception as e:
            logger.error(f"Failed to mark message as processing: {str(e)}")
            
    def mark_sent(self, message_id: str) -> None:
        """Mark message as successfully sent"""
        try:
            self.redis_client.delete(f"{self.processing_key}:{message_id}")
            logger.info(f"Email marked as sent: {message_id}")
            
        except Exception as e:
            logger.error(f"Failed to mark message as sent: {str(e)}")
            
    def mark_failed(self, message_data: Dict, error: str) -> None:
        """Mark message as failed and handle retry logic"""
        try:
            message_id = message_data['id']
            attempts = message_data.get('attempts', 0) + 1
            max_attempts = message_data.get('max_attempts', 3)
            
            if attempts < max_attempts:
                # Retry later
                message_data['attempts'] = attempts
                message_data['last_error'] = error
                
                # Exponential backoff
                delay = (2 ** attempts) * 300  # 5, 10, 20 minutes
                retry_at = datetime.utcnow() + timedelta(seconds=delay)
                
                self.redis_client.zadd(
                    f"{self.queue_key}:scheduled", 
                    {json.dumps(message_data): retry_at.timestamp()}
                )
                
                logger.info(f"Email scheduled for retry {attempts}/{max_attempts}: {message_id}")
            else:
                # Move to failed queue
                failed_data = {
                    **message_data,
                    'failed_at': datetime.utcnow().isoformat(),
                    'final_error': error
                }
                
                self.redis_client.lpush(self.failed_key, json.dumps(failed_data))
                logger.error(f"Email permanently failed after {attempts} attempts: {message_id}")
                
            # Remove from processing
            self.redis_client.delete(f"{self.processing_key}:{message_id}")
            
        except Exception as e:
            logger.error(f"Failed to mark message as failed: {str(e)}")
            
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        try:
            return {
                'queued': self.redis_client.zcard(self.queue_key),
                'scheduled': self.redis_client.zcard(f"{self.queue_key}:scheduled"),
                'processing': len(self.redis_client.keys(f"{self.processing_key}:*")),
                'failed': self.redis_client.llen(self.failed_key)
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {str(e)}")
            return {'queued': 0, 'scheduled': 0, 'processing': 0, 'failed': 0}

class EmailWorker:
    """Background worker for processing email queue"""
    
    def __init__(self):
        self.queue_manager = EmailQueueManager()
        self.delivery_service = EmailDeliveryService()
        self.running = False
        self.worker_thread = None
        
    def start(self) -> None:
        """Start the email worker"""
        if self.running:
            return
            
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Email worker started")
        
    def stop(self) -> None:
        """Stop the email worker"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        logger.info("Email worker stopped")
        
    def _worker_loop(self) -> None:
        """Main worker loop"""
        while self.running:
            try:
                # Get next message
                message_data = self.queue_manager.get_next_message()
                
                if not message_data:
                    # No messages, sleep briefly
                    time.sleep(5)
                    continue
                    
                # Mark as processing
                self.queue_manager.mark_processing(message_data)
                
                # Create EmailMessage object
                message_dict = message_data['message']
                message = EmailMessage(**message_dict)
                
                # Send email
                result = self.delivery_service.send_email(message)
                
                if result['success']:
                    self.queue_manager.mark_sent(message_data['id'])
                else:
                    self.queue_manager.mark_failed(message_data, result['error'])
                    
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
                if 'message_data' in locals():
                    self.queue_manager.mark_failed(message_data, str(e))
                    
                # Sleep on error to avoid tight loop
                time.sleep(30)

class EmailService:
    """Main email service facade"""
    
    def __init__(self):
        self.queue_manager = EmailQueueManager()
        self.delivery_service = EmailDeliveryService()
        self.template_engine = EmailTemplateEngine()
        self.worker = EmailWorker()
        
        # Start worker if configured
        if current_app.config.get('EMAIL_WORKER_ENABLED', True):
            self.worker.start()
            
    def send_email(self, 
                   to: Union[str, List[str]], 
                   subject: str, 
                   template: str, 
                   context: Dict[str, Any],
                   **kwargs) -> str:
        """Send email (adds to queue)"""
        
        message = EmailMessage(
            to=to,
            subject=subject,
            template=template,
            context=context,
            **kwargs
        )
        
        return self.queue_manager.add_to_queue(message)
        
    def send_immediate(self, 
                      to: Union[str, List[str]], 
                      subject: str, 
                      template: str, 
                      context: Dict[str, Any],
                      **kwargs) -> Dict[str, Any]:
        """Send email immediately (bypasses queue)"""
        
        message = EmailMessage(
            to=to,
            subject=subject,
            template=template,
            context=context,
            **kwargs
        )
        
        return self.delivery_service.send_email(message)
        
    def send_task_notification(self, task: Task, notification_type: str, recipients: List[str]) -> str:
        """Send task-related notification"""
        
        context = {
            'task': task,
            'notification_type': notification_type,
            'task_url': f"{current_app.config.get('APP_URL', 'http://localhost:3000')}/tasks/{task.id}"
        }
        
        subject_templates = {
            'created': f"[Action Plan] Nouvelle tâche créée: {task.po_number or task.action_description[:50]}",
            'updated': f"[Action Plan] Tâche mise à jour: {task.po_number or task.action_description[:50]}",
            'completed': f"[Action Plan] Tâche terminée: {task.po_number or task.action_description[:50]}",
            'overdue': f"[Action Plan] Tâche en retard: {task.po_number or task.action_description[:50]}",
            'deadline_reminder': f"[Action Plan] Rappel d'échéance: {task.po_number or task.action_description[:50]}"
        }
        
        return self.send_email(
            to=recipients,
            subject=subject_templates.get(notification_type, f"[Action Plan] Notification: {task.po_number}"),
            template=f'task_{notification_type}.html',
            context=context,
            task_id=str(task.id),
            email_type='task_notification'
        )
        
    def send_weekly_report(self, user: User, report_data: Dict[str, Any]) -> str:
        """Send weekly report email"""
        
        context = {
            'user': user,
            'report_data': report_data,
            'week_start': report_data.get('week_start'),
            'week_end': report_data.get('week_end')
        }
        
        return self.send_email(
            to=user.email,
            subject=f"[Action Plan] Rapport hebdomadaire - {report_data.get('week_start', '').strftime('%d/%m/%Y')}",
            template='weekly_report.html',
            context=context,
            user_id=str(user.id),
            email_type='weekly_report',
            priority=EmailPriority.NORMAL
        )
        
    def send_sync_notification(self, user_id: str, sync_type: str, result: Dict[str, Any]) -> str:
        """Send synchronization notification"""
        
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
            
        context = {
            'user': user,
            'sync_type': sync_type,
            'result': result,
            'success': result.get('success', False)
        }
        
        subject = f"[Action Plan] Synchronisation {sync_type} - {'Réussie' if result.get('success') else 'Échouée'}"
        
        return self.send_email(
            to=user.email,
            subject=subject,
            template='sync_notification.html',
            context=context,
            user_id=user_id,
            email_type='sync_notification',
            priority=EmailPriority.HIGH if not result.get('success') else EmailPriority.NORMAL
        )
        
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get email queue statistics"""
        return self.queue_manager.get_queue_stats()
        
    def get_email_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get email delivery statistics"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            total_sent = EmailLog.query.filter(
                EmailLog.sent_at >= since_date,
                EmailLog.status == 'sent'
            ).count()
            
            total_failed = EmailLog.query.filter(
                EmailLog.sent_at >= since_date,
                EmailLog.status == 'failed'
            ).count()
            
            avg_duration = db.session.query(
                db.func.avg(EmailLog.duration_seconds)
            ).filter(
                EmailLog.sent_at >= since_date,
                EmailLog.status == 'sent'
            ).scalar() or 0
            
            # Get stats by email type
            type_stats = db.session.query(
                EmailLog.email_type,
                db.func.count(EmailLog.id)
            ).filter(
                EmailLog.sent_at >= since_date
            ).group_by(EmailLog.email_type).all()
            
            return {
                'total_sent': total_sent,
                'total_failed': total_failed,
                'success_rate': (total_sent / (total_sent + total_failed) * 100) if (total_sent + total_failed) > 0 else 0,
                'avg_duration_seconds': round(avg_duration, 2),
                'by_type': dict(type_stats),
                'queue_stats': self.get_queue_stats()
            }
            
        except Exception as e:
            logger.error(f"Failed to get email stats: {str(e)}")
            return {
                'total_sent': 0,
                'total_failed': 0,
                'success_rate': 0,
                'avg_duration_seconds': 0,
                'by_type': {},
                'queue_stats': self.get_queue_stats()
            }

# Global service instance
_email_service = None

def get_email_service() -> EmailService:
    """Get email service singleton"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

# Convenience functions
def send_email(to: Union[str, List[str]], subject: str, template: str, context: Dict[str, Any], **kwargs) -> str:
    """Send email via service"""
    return get_email_service().send_email(to, subject, template, context, **kwargs)

def send_task_notification(task: Task, notification_type: str, recipients: List[str]) -> str:
    """Send task notification"""
    return get_email_service().send_task_notification(task, notification_type, recipients)

def send_weekly_report(user: User, report_data: Dict[str, Any]) -> str:
    """Send weekly report"""
    return get_email_service().send_weekly_report(user, report_data)