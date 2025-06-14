# ===================================================================
# email-service/templates.py - Email Template Manager
# ===================================================================

import os
from typing import Dict, Tuple, Optional
from jinja2 import Environment, FileSystemLoader, Template
from pathlib import Path
import structlog
from premailer import transform

logger = structlog.get_logger(__name__)

class EmailTemplateManager:
    """Manages email templates with multi-language support"""
    
    def __init__(self, template_dir: str = "templates"):
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(exist_ok=True)
        
        # Setup Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Default context
        self.default_context = {
            'company_name': 'TechMac',
            'system_name': 'Action Plan Management System',
            'base_url': os.getenv('FRONTEND_URL', 'http://localhost:3000'),
            'support_email': os.getenv('SUPPORT_EMAIL', 'support@techmac.ma'),
            'current_year': '2024'
        }
        
        # Initialize templates
        self._create_default_templates()
        
        logger.info("Email template manager initialized", template_dir=str(self.template_dir))
    
    def render_template(self, template_name: str, context: Dict, language: str = 'fr') -> Tuple[str, str]:
        """Render email template to HTML and text"""
        try:
            # Merge context with defaults
            full_context = {**self.default_context, **context}
            
            # Get template file names
            html_template_name = f"{template_name}_{language}.html"
            text_template_name = f"{template_name}_{language}.txt"
            
            # Fallback to French if language not found
            if not (self.template_dir / html_template_name).exists():
                html_template_name = f"{template_name}_fr.html"
                text_template_name = f"{template_name}_fr.txt"
            
            # Render HTML template
            html_content = ""
            try:
                html_template = self.jinja_env.get_template(html_template_name)
                html_content = html_template.render(full_context)
                
                # Process CSS inline
                html_content = transform(html_content)
                
            except Exception as e:
                logger.warning("HTML template not found, using inline template", 
                             template=html_template_name, error=str(e))
                html_content = self._get_inline_template(template_name, full_context, language)
            
            # Render text template
            text_content = ""
            try:
                text_template = self.jinja_env.get_template(text_template_name)
                text_content = text_template.render(full_context)
            except Exception as e:
                logger.warning("Text template not found, generating from HTML", 
                             template=text_template_name, error=str(e))
                text_content = self._html_to_text(html_content)
            
            return html_content, text_content
            
        except Exception as e:
            logger.error("Template rendering failed", error=str(e), template=template_name)
            return self._get_fallback_template(context), "Email content not available"
    
    def _create_default_templates(self):
        """Create default email templates"""
        templates = {
            'base_fr.html': self._get_base_template(),
            'task_assigned_fr.html': self._get_task_assigned_template(),
            'deadline_reminder_fr.html': self._get_deadline_reminder_template(),
            'task_completed_fr.html': self._get_task_completed_template(),
            'weekly_report_fr.html': self._get_weekly_report_template(),
            'task_assigned_fr.txt': self._get_task_assigned_text(),
            'deadline_reminder_fr.txt': self._get_deadline_reminder_text(),
            'task_completed_fr.txt': self._get_task_completed_text(),
            'weekly_report_fr.txt': self._get_weekly_report_text()
        }
        
        for template_name, content in templates.items():
            template_path = self.template_dir / template_name
            if not template_path.exists():
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info("Created default template", template=template_name)
    
    def _get_base_template(self) -> str:
        """Base email template"""
        return '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ system_name }}{% endblock %}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #1976d2 0%, #dc004e 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 300;
        }
        .content {
            padding: 30px 20px;
        }
        .task-details {
            background: #f8f9fa;
            border-left: 4px solid #1976d2;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }
        .button {
            display: inline-block;
            background: #1976d2;
            color: white;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 5px;
            font-weight: 600;
            margin: 20px 0;
        }
        .footer {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #666;
            border-top: 1px solid #dee2e6;
        }
        .priority-high { border-left-color: #dc3545; }
        .priority-medium { border-left-color: #ffc107; }
        .priority-low { border-left-color: #28a745; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            {% block header %}
            <h1>{{ system_name }}</h1>
            <p>{{ company_name }}</p>
            {% endblock %}
        </div>
        
        <div class="content">
            {% block content %}{% endblock %}
        </div>
        
        <div class="footer">
            {% block footer %}
            <p>© {{ current_year }} {{ company_name }}. Tous droits réservés.</p>
            <p>Ceci est un email automatique, merci de ne pas répondre.</p>
            <p>Pour toute question, contactez : {{ support_email }}</p>
            {% endblock %}
        </div>
    </div>
</body>
</html>'''
    
    def _get_task_assigned_template(self) -> str:
        """Task assigned email template"""
        return '''{% extends "base_fr.html" %}

{% block title %}Nouvelle tâche assignée - {{ system_name }}{% endblock %}

{% block header %}
<h1>🎯 Nouvelle Tâche Assignée</h1>
<p>{{ company_name }} - {{ system_name }}</p>
{% endblock %}

{% block content %}
<h2>Bonjour {{ user_name }},</h2>

<p>Une nouvelle tâche vous a été assignée dans le système de gestion des plans d'action.</p>

<div class="task-details {% if task.priority %}priority-{{ task.priority.lower() }}{% endif %}">
    <h3>📋 Détails de la tâche</h3>
    <p><strong>Description :</strong> {{ task.action_description }}</p>
    <p><strong>Client :</strong> {{ task.customer }}</p>
    <p><strong>Demandeur :</strong> {{ task.requester }}</p>
    {% if task.po_number %}<p><strong>N° PO :</strong> {{ task.po_number }}</p>{% endif %}
    {% if task.category %}<p><strong>Catégorie :</strong> {{ task.category }}</p>{% endif %}
    {% if task.priority %}<p><strong>Priorité :</strong> {{ task.priority }}</p>{% endif %}
    {% if task.deadline %}<p><strong>Échéance :</strong> {{ task.deadline }}</p>{% endif %}
    {% if task.notes %}<p><strong>Notes :</strong> {{ task.notes }}</p>{% endif %}
</div>

<p>Veuillez consulter la tâche et prendre les mesures nécessaires.</p>

<a href="{{ base_url }}/tasks/{{ task.id }}" class="button">Voir la Tâche</a>

<p>Si vous avez des questions, n'hésitez pas à contacter votre manager ou l'équipe support.</p>
{% endblock %}'''
    
    def _get_deadline_reminder_template(self) -> str:
        """Deadline reminder email template"""
        return '''{% extends "base_fr.html" %}

{% block title %}Rappel d'échéance - {{ system_name }}{% endblock %}

{% block header %}
<h1>⏰ Rappel d'Échéance</h1>
<p>{{ company_name }} - {{ system_name }}</p>
{% endblock %}

{% block content %}
<h2>Bonjour {{ user_name }},</h2>

<p>Une tâche qui vous est assignée arrive bientôt à échéance.</p>

<div style="text-align: center; margin: 20px 0;">
    <div style="background: {% if days_remaining <= 1 %}#dc3545{% elif days_remaining <= 3 %}#ffc107{% else %}#17a2b8{% endif %}; 
                color: white; padding: 15px; border-radius: 50px; display: inline-block; font-size: 18px; font-weight: bold;">
        {% if days_remaining <= 0 %}
            🚨 ÉCHÉANCE DÉPASSÉE
        {% elif days_remaining == 1 %}
            ⚠️ 1 JOUR RESTANT
        {% else %}
            📅 {{ days_remaining }} JOURS RESTANTS
        {% endif %}
    </div>
</div>

<div class="task-details">
    <h3>📋 Détails de la tâche</h3>
    <p><strong>Description :</strong> {{ task.action_description }}</p>
    <p><strong>Client :</strong> {{ task.customer }}</p>
    <p><strong>Statut :</strong> {{ task.status }}</p>
    {% if task.deadline %}<p><strong>Échéance :</strong> {{ task.deadline }}</p>{% endif %}
    {% if task.priority %}<p><strong>Priorité :</strong> {{ task.priority }}</p>{% endif %}
</div>

{% if days_remaining <= 0 %}
<p style="color: #dc3545; font-weight: bold;">⚠️ Cette tâche est en retard. Veuillez la traiter en priorité ou mettre à jour son statut.</p>
{% else %}
<p>Veuillez prendre les mesures nécessaires pour respecter l'échéance.</p>
{% endif %}

<a href="{{ base_url }}/tasks/{{ task.id }}" class="button">Voir la Tâche</a>
{% endblock %}'''
    
    def _get_task_completed_template(self) -> str:
        """Task completed email template"""
        return '''{% extends "base_fr.html" %}

{% block title %}Tâche terminée - {{ system_name }}{% endblock %}

{% block header %}
<h1>✅ Tâche Terminée</h1>
<p>{{ company_name }} - {{ system_name }}</p>
{% endblock %}

{% block content %}
<h2>Bonjour {{ user_name }},</h2>

<div style="text-align: center; margin: 20px 0; font-size: 48px;">
    🎉
</div>

<p>Excellente nouvelle ! La tâche suivante a été marquée comme terminée :</p>

<div class="task-details">
    <h3>📋 Détails de la tâche</h3>
    <p><strong>Description :</strong> {{ task.action_description }}</p>
    <p><strong>Client :</strong> {{ task.customer }}</p>
    <p><strong>Responsable :</strong> {{ task.responsible }}</p>
    {% if task.deadline %}<p><strong>Échéance :</strong> {{ task.deadline }}</p>{% endif %}
    <p><strong>Date de completion :</strong> {{ completion_date }}</p>
</div>

<p>Merci pour votre excellent travail ! 👏</p>

<a href="{{ base_url }}/tasks/{{ task.id }}" class="button">Voir la Tâche</a>
{% endblock %}'''
    
    def _get_weekly_report_template(self) -> str:
        """Weekly report email template"""
        return '''{% extends "base_fr.html" %}

{% block title %}Rapport Hebdomadaire - {{ system_name }}{% endblock %}

{% block header %}
<h1>📊 Rapport Hebdomadaire</h1>
<p>Semaine du {{ week_start }}</p>
{% endblock %}

{% block content %}
<h2>Bonjour {{ user_name }},</h2>

<p>Voici le résumé des activités de cette semaine :</p>

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0;">
    <div style="background: #e3f2fd; padding: 20px; text-align: center; border-radius: 8px;">
        <div style="font-size: 24px; font-weight: bold; color: #1976d2;">{{ stats.tasks_created }}</div>
        <div style="font-size: 12px; color: #666; text-transform: uppercase;">Tâches Créées</div>
    </div>
    <div style="background: #e8f5e8; padding: 20px; text-align: center; border-radius: 8px;">
        <div style="font-size: 24px; font-weight: bold; color: #2e7d32;">{{ stats.tasks_completed }}</div>
        <div style="font-size: 12px; color: #666; text-transform: uppercase;">Tâches Terminées</div>
    </div>
    <div style="background: #ffebee; padding: 20px; text-align: center; border-radius: 8px;">
        <div style="font-size: 24px; font-weight: bold; color: #d32f2f;">{{ stats.tasks_overdue }}</div>
        <div style="font-size: 12px; color: #666; text-transform: uppercase;">Tâches en Retard</div>
    </div>
</div>

{% if top_performers %}
<div style="background: white; padding: 15px; margin: 15px 0; border-radius: 8px; border: 1px solid #dee2e6;">
    <h3>🏆 Top Performers de la Semaine</h3>
    {% for performer in top_performers %}
    <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #eee;">
        <span>{{ performer.name }}</span>
        <strong>{{ performer.completed }} tâche{{ 's' if performer.completed > 1 else '' }} terminée{{ 's' if performer.completed > 1 else '' }}</strong>
    </div>
    {% endfor %}
</div>
{% endif %}

<p>Continuez le bon travail ! 💪</p>

<a href="{{ base_url }}/analytics" class="button">Voir le Tableau de Bord</a>
{% endblock %}'''
    
    def _get_task_assigned_text(self) -> str:
        """Text version of task assigned email"""
        return '''Bonjour {{ user_name }},

Une nouvelle tâche vous a été assignée dans le système de gestion des plans d'action.

DÉTAILS DE LA TÂCHE:
- Description: {{ task.action_description }}
- Client: {{ task.customer }}
- Demandeur: {{ task.requester }}
{% if task.po_number %}- N° PO: {{ task.po_number }}{% endif %}
{% if task.category %}- Catégorie: {{ task.category }}{% endif %}
{% if task.priority %}- Priorité: {{ task.priority }}{% endif %}
{% if task.deadline %}- Échéance: {{ task.deadline }}{% endif %}
{% if task.notes %}- Notes: {{ task.notes }}{% endif %}

Veuillez consulter la tâche: {{ base_url }}/tasks/{{ task.id }}

Cordialement,
L'équipe {{ company_name }}'''
    
    def _get_deadline_reminder_text(self) -> str:
        """Text version of deadline reminder email"""
        return '''Bonjour {{ user_name }},

RAPPEL D'ÉCHÉANCE - {% if days_remaining <= 0 %}TÂCHE EN RETARD{% elif days_remaining == 1 %}1 JOUR RESTANT{% else %}{{ days_remaining }} JOURS RESTANTS{% endif %}

Une tâche qui vous est assignée {% if days_remaining <= 0 %}est en retard{% else %}arrive à échéance{% endif %}.

DÉTAILS DE LA TÂCHE:
- Description: {{ task.action_description }}
- Client: {{ task.customer }}
- Statut: {{ task.status }}
{% if task.deadline %}- Échéance: {{ task.deadline }}{% endif %}

{% if days_remaining <= 0 %}Action urgente requise: {{ base_url }}/tasks/{{ task.id }}{% else %}Consulter la tâche: {{ base_url }}/tasks/{{ task.id }}

Cordialement,
L'équipe {{ company_name }}'''
    
    def _get_weekly_report_text(self) -> str:
        """Text version of weekly report email"""
        return '''Bonjour {{ user_name }},

RAPPORT HEBDOMADAIRE - Semaine du {{ week_start }}

RÉSUMÉ DES ACTIVITÉS:
- Tâches créées: {{ stats.tasks_created }}
- Tâches terminées: {{ stats.tasks_completed }}
- Tâches en retard: {{ stats.tasks_overdue }}

{% if top_performers %}TOP PERFORMERS:
{% for performer in top_performers %}- {{ performer.name }}: {{ performer.completed }} tâche{{ 's' if performer.completed > 1 else '' }} terminée{{ 's' if performer.completed > 1 else '' }}
{% endfor %}{% endif %}

Tableau de bord: {{ base_url }}/analytics

Cordialement,
L'équipe {{ company_name }}'''
    
    def _get_inline_template(self, template_name: str, context: Dict, language: str) -> str:
        """Get inline template when file template not found"""
        templates = {
            'task_assigned': f'''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Nouvelle tâche assignée</h2>
                <p>Bonjour {context.get('user_name', 'Utilisateur')},</p>
                <p>Une nouvelle tâche vous a été assignée:</p>
                <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #1976d2;">
                    <strong>{context.get('task', {}).get('action_description', 'Description non disponible')}</strong><br>
                    Client: {context.get('task', {}).get('customer', 'Non spécifié')}
                </div>
                <p><a href="{context.get('base_url', '#')}/tasks/{context.get('task', {}).get('id', '')}" 
                   style="background: #1976d2; color: white; padding: 10px 20px; text-decoration: none;">
                   Voir la tâche</a></p>
            </div>
            ''',
            'deadline_reminder': f'''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Rappel d'échéance</h2>
                <p>Bonjour {context.get('user_name', 'Utilisateur')},</p>
                <p>Une tâche arrive à échéance:</p>
                <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107;">
                    <strong>{context.get('task', {}).get('action_description', 'Description non disponible')}</strong><br>
                    Échéance: {context.get('task', {}).get('deadline', 'Non spécifiée')}
                </div>
            </div>
            ''',
            'task_completed': f'''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Tâche terminée</h2>
                <p>Bonjour {context.get('user_name', 'Utilisateur')},</p>
                <p>Une tâche a été marquée comme terminée:</p>
                <div style="background: #d4edda; padding: 15px; border-left: 4px solid #28a745;">
                    <strong>{context.get('task', {}).get('action_description', 'Description non disponible')}</strong>
                </div>
            </div>
            ''',
            'weekly_report': f'''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Rapport hebdomadaire</h2>
                <p>Bonjour {context.get('user_name', 'Utilisateur')},</p>
                <p>Résumé de la semaine:</p>
                <div style="background: #f8f9fa; padding: 15px;">
                    Tâches créées: {context.get('stats', {}).get('tasks_created', 0)}<br>
                    Tâches terminées: {context.get('stats', {}).get('tasks_completed', 0)}
                </div>
            </div>
            '''
        }
        
        return templates.get(template_name, self._get_fallback_template(context))
    
    def _get_fallback_template(self, context: Dict) -> str:
        """Fallback template when all else fails"""
        return f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>Notification du système</h2>
            <p>Bonjour {context.get('user_name', 'Utilisateur')},</p>
            <p>Vous avez reçu une notification du système de gestion des plans d'action.</p>
            <p>Veuillez consulter l'application pour plus de détails.</p>
            <p><a href="{context.get('base_url', '#')}" style="background: #1976d2; color: white; padding: 10px 20px; text-decoration: none;">
               Accéder à l'application</a></p>
            <hr>
            <p style="font-size: 12px; color: #666;">
                © {context.get('current_year', '2024')} {context.get('company_name', 'TechMac')}
            </p>
        </div>
        '''
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text"""
        try:
            # Simple HTML to text conversion
            import re
            
            # Remove HTML tags
            text = re.sub('<[^<]+?>', '', html)
            
            # Decode HTML entities
            text = text.replace('&nbsp;', ' ')
            text = text.replace('&amp;', '&')
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&quot;', '"')
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            return text
            
        except Exception as e:
            logger.error("HTML to text conversion failed", error=str(e))
            return "Contenu email non disponible en format texte"
    
    def create_custom_template(self, template_name: str, html_content: str, 
                             text_content: str = None, language: str = 'fr'):
        """Create a custom template"""
        try:
            # Save HTML template
            html_path = self.template_dir / f"{template_name}_{language}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Save text template
            if text_content:
                text_path = self.template_dir / f"{template_name}_{language}.txt"
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
            
            logger.info("Custom template created", template=template_name, language=language)
            return True
            
        except Exception as e:
            logger.error("Failed to create custom template", error=str(e))
            return False
    
    def list_templates(self) -> Dict:
        """List available templates"""
        try:
            templates = {}
            
            for template_file in self.template_dir.glob("*.html"):
                name_parts = template_file.stem.split('_')
                if len(name_parts) >= 2:
                    template_name = '_'.join(name_parts[:-1])
                    language = name_parts[-1]
                    
                    if template_name not in templates:
                        templates[template_name] = []
                    
                    templates[template_name].append(language)
            
            return templates
            
        except Exception as e:
            logger.error("Failed to list templates", error=str(e))
            return {}
    
    def validate_template(self, template_name: str, language: str = 'fr') -> bool:
        """Validate if template exists and is valid"""
        try:
            html_template_name = f"{template_name}_{language}.html"
            template_path = self.template_dir / html_template_name
            
            if not template_path.exists():
                return False
            
            # Try to load and compile the template
            template = self.jinja_env.get_template(html_template_name)
            
            # Test render with minimal context
            test_context = {**self.default_context, 'user_name': 'Test', 'task': {'id': '1'}}
            template.render(test_context)
            
            return True
            
        except Exception as e:
            logger.error("Template validation failed", error=str(e), template=template_name)
            return False{% endif %}

Cordialement,
L'équipe {{ company_name }}'''
    
    def _get_task_completed_text(self) -> str:
        """Text version of task completed email"""
        return '''Bonjour {{ user_name }},

Excellente nouvelle! La tâche suivante a été marquée comme terminée:

DÉTAILS DE LA TÂCHE:
- Description: {{ task.action_description }}
- Client: {{ task.customer }}
- Responsable: {{ task.responsible }}
{% if task.deadline %}- Échéance: {{ task.deadline }}{% endif %}
- Date de completion: {{ completion_date }}

Merci pour votre excellent travail!

Consulter la tâche: {{ base_url }}/tasks/{{ task.id }}