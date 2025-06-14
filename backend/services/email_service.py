# ===================================================================
# backend/services/email_service.py - Email Notification Service
# ===================================================================

import os
import logging
import smtplib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from flask import current_app, render_template_string
import requests

from app.models import User, Task, Notification
from app import db

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending email notifications"""
    
    def __init__(self):
        self.smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.office365.com')
        self.smtp_port = current_app.config.get('MAIL_PORT', 587)
        self.smtp_user = current_app.config.get('MAIL_USERNAME')
        self.smtp_password = current_app.config.get('MAIL_PASSWORD')
        self.use_tls = current_app.config.get('MAIL_USE_TLS', True)
        self.from_address = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@techmac.ma')
        self.from_name = current_app.config.get('EMAIL_FROM_NAME', 'Action Plan Management System')
        
        # Microsoft Graph API settings
        self.use_graph_api = current_app.config.get('EMAIL_GRAPH_ENABLED', False)
        self.ms_client_id = current_app.config.get('MS_CLIENT_ID')
        self.ms_client_secret = current_app.config.get('MS_CLIENT_SECRET')
        self.ms_tenant_id = current_app.config.get('MS_TENANT_ID')
    
    def send_email(self, to_email: str, subject: str, html_body: str, text_body: str = None, attachments: List[Dict] = None) -> bool:
        """Send email using SMTP or Microsoft Graph API"""
        try:
            if self.use_graph_api and self.ms_client_id:
                return self._send_via_graph_api(to_email, subject, html_body, text_body, attachments)
            else:
                return self._send_via_smtp(to_email, subject, html_body, text_body, attachments)
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    def _send_via_smtp(self, to_email: str, subject: str, html_body: str, text_body: str = None, attachments: List[Dict] = None) -> bool:
        """Send email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_address}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text part
            if text_body:
                text_part = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    with open(attachment['path'], 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {attachment["name"]}'
                        )
                        msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email via SMTP to {to_email}: {str(e)}")
            return False
    
    def _send_via_graph_api(self, to_email: str, subject: str, html_body: str, text_body: str = None, attachments: List[Dict] = None) -> bool:
        """Send email via Microsoft Graph API"""
        try:
            # Get access token
            token = self._get_graph_access_token()
            if not token:
                logger.error("Failed to get access token for Graph API")
                return False
            
            # Prepare email message
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": html_body
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": to_email
                            }
                        }
                    ],
                    "from": {
                        "emailAddress": {
                            "address": self.from_address,
                            "name": self.from_name
                        }
                    }
                }
            }
            
            # Add attachments if any
            if attachments:
                message["message"]["attachments"] = []
                for attachment in attachments:
                    with open(attachment['path'], 'rb') as f:
                        import base64
                        content = base64.b64encode(f.read()).decode('utf-8')
                        
                        message["message"]["attachments"].append({
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": attachment["name"],
                            "contentType": attachment.get("content_type", "application/octet-stream"),
                            "contentBytes": content
                        })
            
            # Send email
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f'https://graph.microsoft.com/v1.0/users/{self.from_address}/sendMail',
                headers=headers,
                json=message
            )
            
            if response.status_code == 202:
                logger.info(f"Email sent successfully via Graph API to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email via Graph API: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email via Graph API to {to_email}: {str(e)}")
            return False
    
    def _get_graph_access_token(self) -> Optional[str]:
        """Get access token for Microsoft Graph API"""
        try:
            import msal
            
            app = msal.ConfidentialClientApplication(
                client_id=self.ms_client_id,
                client_credential=self.ms_client_secret,
                authority=f"https://login.microsoftonline.com/{self.ms_tenant_id}"
            )
            
            result = app.acquire_token_for_client(scopes=['https://graph.microsoft.com/.default'])
            
            if 'access_token' in result:
                return result['access_token']
            else:
                logger.error(f"Failed to acquire token: {result.get('error_description', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Graph access token: {str(e)}")
            return None
    
    def send_task_notification(self, task: Task, notification_type: str, users: List[User]) -> bool:
        """Send task-related notification to users"""
        try:
            # Generate email content based on notification type
            subject, html_body, text_body = self._generate_task_email_content(task, notification_type)
            
            success_count = 0
            for user in users:
                if user.email:
                    # Personalize the email
                    personalized_html = html_body.replace('{{user_name}}', user.name)
                    personalized_text = text_body.replace('{{user_name}}', user.name) if text_body else None
                    
                    if self.send_email(user.email, subject, personalized_html, personalized_text):
                        success_count += 1
                        
                        # Create notification record
                        notification = Notification(
                            user_id=user.id,
                            title=subject,
                            message=f"Email sent: {notification_type}",
                            type='info',
                            task_id=task.id
                        )
                        db.session.add(notification)
            
            db.session.commit()
            
            logger.info(f"Task notification sent to {success_count}/{len(users)} users for task {task.id}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending task notification: {str(e)}")
            return False
    
    def _generate_task_email_content(self, task: Task, notification_type: str) -> tuple:
        """Generate email content for task notifications"""
        
        base_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
        task_url = f"{base_url}/tasks/{task.id}"
        
        # Common variables
        context = {
            'task': task,
            'task_url': task_url,
            'base_url': base_url,
            'company_name': 'TechMac',
            'current_year': datetime.now().year
        }
        
        if notification_type == 'task_assigned':
            subject = f"Nouvelle tâche assignée: {task.action_description[:50]}..."
            html_body = self._render_task_assigned_template(context)
            text_body = f"""
Bonjour {{{{user_name}}}},

Une nouvelle tâche vous a été assignée:

Tâche: {task.action_description}
Client: {task.customer}
Échéance: {task.deadline.strftime('%d/%m/%Y') if task.deadline else 'Non définie'}
Priorité: {task.priority}

Voir la tâche: {task_url}

Cordialement,
L'équipe TechMac
            """.strip()
            
        elif notification_type == 'deadline_reminder':
            days_remaining = (task.deadline - datetime.utcnow()).days if task.deadline else 0
            subject = f"Rappel d'échéance: {task.action_description[:50]}... ({days_remaining} jours)"
            html_body = self._render_deadline_reminder_template(context, days_remaining)
            text_body = f"""
Bonjour {{{{user_name}}}},

Rappel: La tâche suivante arrive à échéance dans {days_remaining} jour(s):

Tâche: {task.action_description}
Client: {task.customer}
Échéance: {task.deadline.strftime('%d/%m/%Y') if task.deadline else 'Non définie'}
Statut: {task.status}

Voir la tâche: {task_url}

Cordialement,
L'équipe TechMac
            """.strip()
            
        elif notification_type == 'task_overdue':
            days_overdue = (datetime.utcnow() - task.deadline).days if task.deadline else 0
            subject = f"Tâche en retard: {task.action_description[:50]}... ({days_overdue} jours de retard)"
            html_body = self._render_task_overdue_template(context, days_overdue)
            text_body = f"""
Bonjour {{{{user_name}}}},

URGENT: La tâche suivante est en retard de {days_overdue} jour(s):

Tâche: {task.action_description}
Client: {task.customer}
Échéance: {task.deadline.strftime('%d/%m/%Y') if task.deadline else 'Non définie'}
Statut: {task.status}

Action requise immédiatement: {task_url}

Cordialement,
L'équipe TechMac
            """.strip()
            
        elif notification_type == 'task_completed':
            subject = f"Tâche terminée: {task.action_description[:50]}..."
            html_body = self._render_task_completed_template(context)
            text_body = f"""
Bonjour {{{{user_name}}}},

La tâche suivante a été marquée comme terminée:

Tâche: {task.action_description}
Client: {task.customer}
Responsable: {task.responsible}

Voir la tâche: {task_url}

Cordialement,
L'équipe TechMac
            """.strip()
            
        else:
            subject = f"Mise à jour de tâche: {task.action_description[:50]}..."
            html_body = self._render_task_update_template(context)
            text_body = f"""
Bonjour {{{{user_name}}}},

Une tâche a été mise à jour:

Tâche: {task.action_description}
Client: {task.customer}
Statut: {task.status}

Voir la tâche: {task_url}

Cordialement,
L'équipe TechMac
            """.strip()
        
        return subject, html_body, text_body
    
    def _render_task_assigned_template(self, context: Dict) -> str:
        """Render task assigned email template"""
        template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nouvelle tâche assignée</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #1976d2, #dc004e); color: white; padding: 20px; text-align: center; }
        .content { background: #f9f9f9; padding: 20px; }
        .task-details { background: white; border-left: 4px solid #1976d2; padding: 15px; margin: 15px 0; }
        .button { display: inline-block; background: #1976d2; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⏰ Rappel d'Échéance</h1>
            <p>Système de Gestion des Plans d'Action</p>
        </div>
        
        <div class="content">
            <h2>Bonjour {{user_name}},</h2>
            <p>Une tâche qui vous est assignée arrive bientôt à échéance.</p>
            
            <div class="countdown">
                {{ days_remaining }} jour{{ 's' if days_remaining > 1 else '' }} restant{{ 's' if days_remaining > 1 else '' }}
            </div>
            
            <div class="task-details {{ urgency_class }}">
                <h3>Détails de la tâche</h3>
                <p><strong>Description:</strong> {{ task.action_description }}</p>
                <p><strong>Client:</strong> {{ task.customer }}</p>
                <p><strong>Statut:</strong> {{ task.status }}</p>
                {% if task.deadline %}
                <p><strong>Échéance:</strong> {{ task.deadline.strftime('%d/%m/%Y') }}</p>
                {% endif %}
                <p><strong>Priorité:</strong> {{ task.priority or 'Moyen' }}</p>
            </div>
            
            <p>Veuillez prendre les mesures nécessaires pour respecter l'échéance.</p>
            
            <a href="{{ task_url }}" class="button">Voir la Tâche</a>
        </div>
        
        <div class="footer">
            <p>© {{ current_year }} {{ company_name }}. Tous droits réservés.</p>
            <p>Ceci est un email automatique, merci de ne pas répondre.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return render_template_string(template, **context)
    
    def _render_task_overdue_template(self, context: Dict, days_overdue: int) -> str:
        """Render task overdue email template"""
        context['days_overdue'] = days_overdue
        
        template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tâche en retard</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #f44336, #d32f2f); color: white; padding: 20px; text-align: center; }
        .content { background: #f9f9f9; padding: 20px; }
        .task-details { background: white; border-left: 4px solid #f44336; padding: 15px; margin: 15px 0; }
        .overdue-alert { background: #ffebee; border: 1px solid #f44336; color: #c62828; padding: 15px; margin: 15px 0; border-radius: 5px; text-align: center; }
        .button { display: inline-block; background: #f44336; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Tâche en Retard</h1>
            <p>Action Urgente Requise</p>
        </div>
        
        <div class="content">
            <h2>Bonjour {{user_name}},</h2>
            
            <div class="overdue-alert">
                <strong>URGENT:</strong> Cette tâche est en retard de {{ days_overdue }} jour{{ 's' if days_overdue > 1 else '' }}
            </div>
            
            <div class="task-details">
                <h3>Détails de la tâche</h3>
                <p><strong>Description:</strong> {{ task.action_description }}</p>
                <p><strong>Client:</strong> {{ task.customer }}</p>
                <p><strong>Statut:</strong> {{ task.status }}</p>
                {% if task.deadline %}
                <p><strong>Échéance:</strong> {{ task.deadline.strftime('%d/%m/%Y') }}</p>
                {% endif %}
                <p><strong>Responsable:</strong> {{ task.responsible }}</p>
            </div>
            
            <p>Cette tâche nécessite une attention immédiate. Veuillez mettre à jour le statut ou contacter votre manager.</p>
            
            <a href="{{ task_url }}" class="button">Action Immédiate Requise</a>
        </div>
        
        <div class="footer">
            <p>© {{ current_year }} {{ company_name }}. Tous droits réservés.</p>
            <p>Ceci est un email automatique, merci de ne pas répondre.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return render_template_string(template, **context)
    
    def _render_task_completed_template(self, context: Dict) -> str:
        """Render task completed email template"""
        template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tâche terminée</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #4caf50, #2e7d32); color: white; padding: 20px; text-align: center; }
        .content { background: #f9f9f9; padding: 20px; }
        .task-details { background: white; border-left: 4px solid #4caf50; padding: 15px; margin: 15px 0; }
        .success-icon { text-align: center; font-size: 48px; color: #4caf50; margin: 20px 0; }
        .button { display: inline-block; background: #4caf50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Tâche Terminée</h1>
            <p>Félicitations!</p>
        </div>
        
        <div class="content">
            <h2>Bonjour {{user_name}},</h2>
            
            <div class="success-icon">🎉</div>
            
            <p>Excellente nouvelle! La tâche suivante a été marquée comme terminée:</p>
            
            <div class="task-details">
                <h3>Détails de la tâche</h3>
                <p><strong>Description:</strong> {{ task.action_description }}</p>
                <p><strong>Client:</strong> {{ task.customer }}</p>
                <p><strong>Responsable:</strong> {{ task.responsible }}</p>
                {% if task.deadline %}
                <p><strong>Échéance:</strong> {{ task.deadline.strftime('%d/%m/%Y') }}</p>
                {% endif %}
                <p><strong>Date de completion:</strong> {{ task.updated_at.strftime('%d/%m/%Y à %H:%M') }}</p>
            </div>
            
            <p>Merci pour votre excellent travail!</p>
            
            <a href="{{ task_url }}" class="button">Voir la Tâche</a>
        </div>
        
        <div class="footer">
            <p>© {{ current_year }} {{ company_name }}. Tous droits réservés.</p>
            <p>Ceci est un email automatique, merci de ne pas répondre.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return render_template_string(template, **context)
    
    def _render_task_update_template(self, context: Dict) -> str:
        """Render task update email template"""
        template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mise à jour de tâche</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #2196f3, #1976d2); color: white; padding: 20px; text-align: center; }
        .content { background: #f9f9f9; padding: 20px; }
        .task-details { background: white; border-left: 4px solid #2196f3; padding: 15px; margin: 15px 0; }
        .button { display: inline-block; background: #2196f3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📝 Mise à Jour de Tâche</h1>
            <p>Système de Gestion des Plans d'Action</p>
        </div>
        
        <div class="content">
            <h2>Bonjour {{user_name}},</h2>
            <p>Une tâche qui vous concerne a été mise à jour:</p>
            
            <div class="task-details">
                <h3>Détails de la tâche</h3>
                <p><strong>Description:</strong> {{ task.action_description }}</p>
                <p><strong>Client:</strong> {{ task.customer }}</p>
                <p><strong>Statut:</strong> {{ task.status }}</p>
                <p><strong>Responsable:</strong> {{ task.responsible }}</p>
                {% if task.deadline %}
                <p><strong>Échéance:</strong> {{ task.deadline.strftime('%d/%m/%Y') }}</p>
                {% endif %}
                <p><strong>Dernière mise à jour:</strong> {{ task.updated_at.strftime('%d/%m/%Y à %H:%M') }}</p>
            </div>
            
            <a href="{{ task_url }}" class="button">Voir la Tâche</a>
        </div>
        
        <div class="footer">
            <p>© {{ current_year }} {{ company_name }}. Tous droits réservés.</p>
            <p>Ceci est un email automatique, merci de ne pas répondre.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return render_template_string(template, **context)
    
    def send_weekly_report(self, users: List[User]) -> bool:
        """Send weekly report to users"""
        try:
            # Get week's statistics
            week_start = datetime.utcnow() - timedelta(days=7)
            
            # Calculate statistics
            stats = {
                'tasks_created': Task.query.filter(Task.created_at >= week_start).count(),
                'tasks_completed': Task.query.filter(
                    Task.updated_at >= week_start,
                    Task.status == 'Terminé'
                ).count(),
                'tasks_overdue': Task.query.filter(
                    Task.deadline < datetime.utcnow(),
                    Task.status.notin_(['Terminé', 'Annulé'])
                ).count()
            }
            
            # Get top performers
            from sqlalchemy import func
            top_performers = db.session.query(
                Task.responsible,
                func.count(Task.id).label('completed_count')
            ).filter(
                Task.updated_at >= week_start,
                Task.status == 'Terminé'
            ).group_by(Task.responsible).order_by(
                func.count(Task.id).desc()
            ).limit(3).all()
            
            subject = f"Rapport Hebdomadaire - Semaine du {week_start.strftime('%d/%m/%Y')}"
            
            success_count = 0
            for user in users:
                if user.email and 'manager' in user.roles or 'admin' in user.roles:
                    html_body = self._render_weekly_report_template({
                        'user': user,
                        'stats': stats,
                        'top_performers': top_performers,
                        'week_start': week_start,
                        'company_name': 'TechMac',
                        'current_year': datetime.now().year,
                        'base_url': current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
                    })
                    
                    if self.send_email(user.email, subject, html_body):
                        success_count += 1
            
            logger.info(f"Weekly report sent to {success_count} users")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending weekly report: {str(e)}")
            return False
    
    def _render_weekly_report_template(self, context: Dict) -> str:
        """Render weekly report email template"""
        template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport Hebdomadaire</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #673ab7, #9c27b0); color: white; padding: 20px; text-align: center; }
        .content { background: #f9f9f9; padding: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: white; padding: 15px; text-align: center; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-number { font-size: 24px; font-weight: bold; color: #1976d2; }
        .stat-label { font-size: 12px; color: #666; text-transform: uppercase; }
        .performers-list { background: white; padding: 15px; margin: 15px 0; border-radius: 8px; }
        .performer { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #eee; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Rapport Hebdomadaire</h1>
            <p>Semaine du {{ week_start.strftime('%d/%m/%Y') }}</p>
        </div>
        
        <div class="content">
            <h2>Bonjour {{ user.name }},</h2>
            <p>Voici le résumé des activités de cette semaine:</p>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{{ stats.tasks_created }}</div>
                    <div class="stat-label">Tâches Créées</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ stats.tasks_completed }}</div>
                    <div class="stat-label">Tâches Terminées</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ stats.tasks_overdue }}</div>
                    <div class="stat-label">Tâches en Retard</div>
                </div>
            </div>
            
            {% if top_performers %}
            <div class="performers-list">
                <h3>🏆 Top Performers de la Semaine</h3>
                {% for performer, count in top_performers %}
                <div class="performer">
                    <span>{{ performer }}</span>
                    <strong>{{ count }} tâche{{ 's' if count > 1 else '' }} terminée{{ 's' if count > 1 else '' }}</strong>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            <p>Continuez le bon travail!</p>
            
            <a href="{{ base_url }}/analytics" style="display: inline-block; background: #673ab7; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0;">Voir le Tableau de Bord</a>
        </div>
        
        <div class="footer">
            <p>© {{ current_year }} {{ company_name }}. Tous droits réservés.</p>
            <p>Ceci est un email automatique, merci de ne pas répondre.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return render_template_string(template, **context)

class NotificationService:
    """Service for managing notifications"""
    
    @staticmethod
    def check_deadlines_and_notify():
        """Check for approaching deadlines and send notifications"""
        try:
            email_service = EmailService()
            warning_days = current_app.config.get('DEADLINE_WARNING_DAYS', 3)
            
            # Get tasks with approaching deadlines
            warning_date = datetime.utcnow() + timedelta(days=warning_days)
            approaching_tasks = Task.query.filter(
                Task.deadline <= warning_date,
                Task.deadline >= datetime.utcnow(),
                Task.status.notin_(['Terminé', 'Annulé'])
            ).all()
            
            # Get overdue tasks
            overdue_tasks = Task.query.filter(
                Task.deadline < datetime.utcnow(),
                Task.status.notin_(['Terminé', 'Annulé'])
            ).all()
            
            notification_count = 0
            
            # Send deadline warnings
            for task in approaching_tasks:
                users_to_notify = User.query.filter(
                    db.or_(
                        User.name == task.responsible,
                        User.roles.contains(['manager']),
                        User.roles.contains(['admin'])
                    )
                ).all()
                
                if email_service.send_task_notification(task, 'deadline_reminder', users_to_notify):
                    notification_count += 1
            
            # Send overdue notifications
            for task in overdue_tasks:
                users_to_notify = User.query.filter(
                    db.or_(
                        User.name == task.responsible,
                        User.roles.contains(['manager']),
                        User.roles.contains(['admin'])
                    )
                ).all()
                
                if email_service.send_task_notification(task, 'task_overdue', users_to_notify):
                    notification_count += 1
            
            logger.info(f"Deadline notifications sent: {notification_count} notifications for {len(approaching_tasks)} approaching and {len(overdue_tasks)} overdue tasks")
            
        except Exception as e:
            logger.error(f"Error checking deadlines and sending notifications: {str(e)}")
    
    @staticmethod
    def schedule_weekly_reports():
        """Schedule and send weekly reports"""
        try:
            # Send weekly reports every Monday
            if datetime.utcnow().weekday() == 0:  # Monday
                email_service = EmailService()
                managers_and_admins = User.query.filter(
                    db.or_(
                        User.roles.contains(['manager']),
                        User.roles.contains(['admin'])
                    )
                ).all()
                
                email_service.send_weekly_report(managers_and_admins)
                logger.info("Weekly reports sent")
                
        except Exception as e:
            logger.error(f"Error sending weekly reports: {str(e)}")

# Initialize notification scheduler
def init_notification_scheduler(app):
    """Initialize notification scheduler with Flask app context"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        scheduler = BackgroundScheduler()
        
        with app.app_context():
            if app.config.get('ENABLE_EMAIL_NOTIFICATIONS', True):
                # Check deadlines every hour
                scheduler.add_job(
                    func=NotificationService.check_deadlines_and_notify,
                    trigger=CronTrigger(minute=0),  # Every hour
                    id='deadline_notifications',
                    name='Deadline Notifications',
                    replace_existing=True
                )
                
                # Send weekly reports every Monday at 9 AM
                scheduler.add_job(
                    func=NotificationService.schedule_weekly_reports,
                    trigger=CronTrigger(day_of_week=0, hour=9, minute=0),  # Monday 9 AM
                    id='weekly_reports',
                    name='Weekly Reports',
                    replace_existing=True
                )
                
                scheduler.start()
                logger.info("Notification scheduler initialized")
                
    except Exception as e:
        logger.error(f"Error initializing notification scheduler: {str(e)}"): center; padding: 20px; color: #666; font-size: 12px; }
        .priority-high { border-left-color: #f44336; }
        .priority-medium { border-left-color: #ff9800; }
        .priority-low { border-left-color: #4caf50; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Nouvelle Tâche Assignée</h1>
            <p>Système de Gestion des Plans d'Action</p>
        </div>
        
        <div class="content">
            <h2>Bonjour {{user_name}},</h2>
            <p>Une nouvelle tâche vous a été assignée dans le système de gestion des plans d'action.</p>
            
            <div class="task-details priority-{{ task.priority.lower() if task.priority else 'medium' }}">
                <h3>Détails de la tâche</h3>
                <p><strong>Description:</strong> {{ task.action_description }}</p>
                <p><strong>Client:</strong> {{ task.customer }}</p>
                <p><strong>Demandeur:</strong> {{ task.requester }}</p>
                {% if task.po_number %}
                <p><strong>PO:</strong> {{ task.po_number }}</p>
                {% endif %}
                {% if task.category %}
                <p><strong>Catégorie:</strong> {{ task.category }}</p>
                {% endif %}
                <p><strong>Priorité:</strong> {{ task.priority or 'Moyen' }}</p>
                {% if task.deadline %}
                <p><strong>Échéance:</strong> {{ task.deadline.strftime('%d/%m/%Y') }}</p>
                {% endif %}
                {% if task.notes %}
                <p><strong>Notes:</strong> {{ task.notes }}</p>
                {% endif %}
            </div>
            
            <p>Veuillez consulter la tâche et prendre les mesures nécessaires.</p>
            
            <a href="{{ task_url }}" class="button">Voir la Tâche</a>
        </div>
        
        <div class="footer">
            <p>© {{ current_year }} {{ company_name }}. Tous droits réservés.</p>
            <p>Ceci est un email automatique, merci de ne pas répondre.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return render_template_string(template, **context)
    
    def _render_deadline_reminder_template(self, context: Dict, days_remaining: int) -> str:
        """Render deadline reminder email template"""
        urgency_class = "urgent" if days_remaining <= 1 else "warning" if days_remaining <= 3 else "info"
        context['urgency_class'] = urgency_class
        context['days_remaining'] = days_remaining
        
        template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rappel d'échéance</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #ff9800, #f44336); color: white; padding: 20px; text-align: center; }
        .content { background: #f9f9f9; padding: 20px; }
        .task-details { background: white; border-left: 4px solid #ff9800; padding: 15px; margin: 15px 0; }
        .urgent { border-left-color: #f44336; }
        .warning { border-left-color: #ff9800; }
        .info { border-left-color: #2196f3; }
        .countdown { text-align: center; font-size: 24px; font-weight: bold; color: #f44336; margin: 20px 0; }
        .button { display: inline-block; background: #ff9800; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }
        .footer { text-align