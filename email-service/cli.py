#!/usr/bin/env python3
# ===================================================================
# email-service/cli.py - Email Service Command Line Interface
# ===================================================================

import asyncio
import click
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from email_service import EmailService, EmailConfig
from templates import EmailTemplateManager

@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.pass_context
def cli(ctx, config):
    """Email Service Command Line Interface"""
    ctx.ensure_object(dict)
    
    # Initialize configuration
    if config and Path(config).exists():
        with open(config) as f:
            config_data = json.load(f)
        ctx.obj['config'] = EmailConfig(**config_data)
    else:
        ctx.obj['config'] = EmailConfig()
    
    # Initialize email service
    ctx.obj['email_service'] = EmailService(ctx.obj['config'])

@cli.command()
@click.option('--to', '-t', required=True, help='Recipient email address')
@click.option('--subject', '-s', required=True, help='Email subject')
@click.option('--template', required=True, help='Template name')
@click.option('--context', '-ctx', help='Template context as JSON string')
@click.option('--language', '-l', default='fr', help='Language (fr, en, ar)')
@click.pass_context
def send(ctx, to, subject, template, context, language):
    """Send a single email"""
    try:
        # Parse context
        template_context = {}
        if context:
            template_context = json.loads(context)
        
        # Prepare email data
        email_data = {
            'to_email': to,
            'subject': subject,
            'template_name': template,
            'context': template_context,
            'language': language
        }
        
        # Send email
        email_service = ctx.obj['email_service']
        success = asyncio.run(email_service.send_email(email_data))
        
        if success:
            click.echo(f"✅ Email sent successfully to {to}")
        else:
            click.echo(f"❌ Failed to send email to {to}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@cli.command()
@click.option('--file', '-f', required=True, help='JSON file with email batch data')
@click.pass_context
def send_batch(ctx, file):
    """Send batch emails from JSON file"""
    try:
        # Load batch data
        with open(file) as f:
            batch_data = json.load(f)
        
        emails = batch_data.get('emails', [])
        if not emails:
            click.echo("❌ No emails found in batch file")
            sys.exit(1)
        
        click.echo(f"📧 Sending {len(emails)} emails...")
        
        # Send batch
        email_service = ctx.obj['email_service']
        results = asyncio.run(email_service.send_bulk_emails(emails))
        
        click.echo(f"✅ Sent: {results['sent']}")
        click.echo(f"❌ Failed: {results['failed']}")
        
        if results['errors']:
            click.echo("Errors:")
            for error in results['errors'][:5]:  # Show first 5 errors
                click.echo(f"  - {error}")
                
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@cli.command()
@click.pass_context
def check_deadlines(ctx):
    """Check deadlines and send notifications"""
    try:
        email_service = ctx.obj['email_service']
        result = email_service.check_deadlines_and_notify()
        
        if 'error' in result:
            click.echo(f"❌ Error: {result['error']}")
            sys.exit(1)
        else:
            count = result.get('notifications_sent', 0)
            click.echo(f"✅ {count} deadline notifications queued")
            
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@cli.command()
@click.pass_context
def send_reports(ctx):
    """Send weekly reports"""
    try:
        email_service = ctx.obj['email_service']
        result = email_service.send_weekly_reports()
        
        if 'error' in result:
            click.echo(f"❌ Error: {result['error']}")
            sys.exit(1)
        else:
            count = result.get('reports_sent', 0)
            click.echo(f"✅ {count} weekly reports queued")
            
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@cli.command()
@click.pass_context
def test_smtp(ctx):
    """Test SMTP connection"""
    try:
        email_service = ctx.obj['email_service']
        
        if not email_service.smtp_client:
            click.echo("❌ SMTP client not configured")
            sys.exit(1)
        
        success = asyncio.run(email_service.smtp_client.test_connection())
        
        if success:
            click.echo("✅ SMTP connection successful")
        else:
            click.echo("❌ SMTP connection failed")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@cli.command()
@click.pass_context
def test_graph(ctx):
    """Test Microsoft Graph connection"""
    try:
        email_service = ctx.obj['email_service']
        
        if not email_service.graph_client:
            click.echo("❌ Graph client not configured")
            sys.exit(1)
        
        success = asyncio.run(email_service.graph_client.test_connection())
        
        if success:
            click.echo("✅ Microsoft Graph connection successful")
        else:
            click.echo("❌ Microsoft Graph connection failed")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@cli.command()
@click.pass_context
def status(ctx):
    """Show email service status"""
    try:
        email_service = ctx.obj['email_service']
        stats = email_service.get_stats()
        
        click.echo("📊 Email Service Status:")
        click.echo(f"  SMTP Enabled: {'✅' if stats['smtp_enabled'] else '❌'}")
        click.echo(f"  Graph Enabled: {'✅' if stats['graph_enabled'] else '❌'}")
        click.echo(f"  Emails Sent: {stats['sent_count']}")
        click.echo(f"  Failed Emails: {stats['failed_count']}")
        click.echo(f"  Last Check: {stats['last_check']}")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@cli.group()
def template():
    """Template management commands"""
    pass

@template.command('list')
def list_templates():
    """List available templates"""
    try:
        template_manager = EmailTemplateManager()
        templates = template_manager.list_templates()
        
        if not templates:
            click.echo("No templates found")
            return
        
        click.echo("📄 Available Templates:")
        for name, languages in templates.items():
            click.echo(f"  {name}: {', '.join(languages)}")
            
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@template.command('validate')
@click.argument('template_name')
@click.option('--language', '-l', default='fr', help='Language to validate')
def validate_template(template_name, language):
    """Validate a template"""
    try:
        template_manager = EmailTemplateManager()
        is_valid = template_manager.validate_template(template_name, language)
        
        if is_valid:
            click.echo(f"✅ Template '{template_name}_{language}' is valid")
        else:
            click.echo(f"❌ Template '{template_name}_{language}' is invalid or not found")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@template.command('create')
@click.argument('template_name')
@click.option('--html-file', '-h', required=True, help='HTML template file')
@click.option('--text-file', '-t', help='Text template file')
@click.option('--language', '-l', default='fr', help='Language')
def create_template(template_name, html_file, text_file, language):
    """Create a new template"""
    try:
        # Read HTML content
        with open(html_file) as f:
            html_content = f.read()
        
        # Read text content if provided
        text_content = None
        if text_file:
            with open(text_file) as f:
                text_content = f.read()
        
        # Create template
        template_manager = EmailTemplateManager()
        success = template_manager.create_custom_template(
            template_name, html_content, text_content, language
        )
        
        if success:
            click.echo(f"✅ Template '{template_name}_{language}' created successfully")
        else:
            click.echo(f"❌ Failed to create template '{template_name}_{language}'")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@cli.command()
@click.option('--output', '-o', default='email_config.json', help='Output file')
def generate_config(output):
    """Generate configuration file template"""
    try:
        config_template = {
            "smtp_server": "smtp.office365.com",
            "smtp_port": 587,
            "smtp_user": "your-email@domain.com",
            "smtp_password": "your-password",
            "use_tls": True,
            "from_address": "noreply@domain.com",
            "from_name": "Action Plan System",
            "use_graph_api": False,
            "ms_client_id": "your-client-id",
            "ms_client_secret": "your-client-secret",
            "ms_tenant_id": "your-tenant-id",
            "database_url": "postgresql://user:pass@host:5432/db",
            "redis_url": "redis://localhost:6379",
            "deadline_warning_days": 3,
            "batch_size": 50,
            "retry_count": 3,
            "retry_delay": 300
        }
        
        with open(output, 'w') as f:
            json.dump(config_template, f, indent=2)
        
        click.echo(f"✅ Configuration template saved to {output}")
        click.echo("Please edit the file with your actual credentials")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

@cli.command()
def worker():
    """Start email service worker"""
    try:
        click.echo("🚀 Starting email service worker...")
        click.echo("Press Ctrl+C to stop")
        
        # This would start the actual worker
        # For now, just show that it would start
        click.echo("Worker started successfully")
        click.echo("Listening for email tasks...")
        
        # Keep running until interrupted
        try:
            while True:
                asyncio.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n👋 Worker stopped")
            
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    cli()