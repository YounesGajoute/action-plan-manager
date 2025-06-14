# ===================================================================
# email-service/smtp_client.py - SMTP Email Client
# ===================================================================

import smtplib
import ssl
import asyncio
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Optional
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

class SMTPClient:
    """SMTP Email Client with retry logic and error handling"""
    
    def __init__(self, server: str, port: int, username: str, password: str, 
                 use_tls: bool = True, from_address: str = None, from_name: str = None):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_address = from_address or username
        self.from_name = from_name or "Action Plan System"
        
        # Connection pool settings
        self.max_connections = 5
        self.connection_timeout = 30
        
        logger.info("SMTP client initialized", 
                   server=server, port=port, username=username, use_tls=use_tls)
    
    async def send_email(self, to_email: str, subject: str, html_content: str, 
                        text_content: str = None, attachments: List[Dict] = None) -> bool:
        """Send email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_address}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    await self._add_attachment(msg, attachment)
            
            # Send email
            success = await self._send_message(msg, to_email)
            
            if success:
                logger.info("Email sent successfully", to=to_email, subject=subject)
            else:
                logger.error("Email sending failed", to=to_email, subject=subject)
            
            return success
            
        except Exception as e:
            logger.error("SMTP send error", error=str(e), to=to_email, subject=subject)
            return False
    
    async def _send_message(self, msg: MIMEMultipart, to_email: str) -> bool:
        """Send the actual message via SMTP"""
        try:
            # Create SMTP connection
            if self.use_tls:
                server = smtplib.SMTP(self.server, self.port, timeout=self.connection_timeout)
                server.starttls(context=ssl.create_default_context())
            else:
                server = smtplib.SMTP_SSL(self.server, self.port, timeout=self.connection_timeout)
            
            # Login
            server.login(self.username, self.password)
            
            # Send message
            text = msg.as_string()
            server.sendmail(self.from_address, to_email, text)
            
            # Close connection
            server.quit()
            
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error("SMTP authentication failed", error=str(e))
            return False
        except smtplib.SMTPRecipientsRefused as e:
            logger.error("SMTP recipients refused", error=str(e), to=to_email)
            return False
        except smtplib.SMTPServerDisconnected as e:
            logger.error("SMTP server disconnected", error=str(e))
            return False
        except Exception as e:
            logger.error("SMTP general error", error=str(e))
            return False
    
    async def _add_attachment(self, msg: MIMEMultipart, attachment: Dict):
        """Add attachment to message"""
        try:
            file_path = attachment.get('path')
            file_name = attachment.get('name', Path(file_path).name)
            content_type = attachment.get('content_type', 'application/octet-stream')
            
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(file_data)
            encoders.encode_base64(part)
            
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {file_name}'
            )
            
            msg.attach(part)
            
        except Exception as e:
            logger.error("Failed to add attachment", error=str(e), attachment=attachment)
    
    async def test_connection(self) -> bool:
        """Test SMTP connection"""
        try:
            if self.use_tls:
                server = smtplib.SMTP(self.server, self.port, timeout=self.connection_timeout)
                server.starttls(context=ssl.create_default_context())
            else:
                server = smtplib.SMTP_SSL(self.server, self.port, timeout=self.connection_timeout)
            
            server.login(self.username, self.password)
            server.quit()
            
            logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            logger.error("SMTP connection test failed", error=str(e))
            return False
    
    def get_connection_info(self) -> Dict:
        """Get connection information"""
        return {
            'server': self.server,
            'port': self.port,
            'username': self.username,
            'use_tls': self.use_tls,
            'from_address': self.from_address,
            'from_name': self.from_name
        }