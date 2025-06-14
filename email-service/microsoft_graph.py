# ===================================================================
# email-service/microsoft_graph.py - Microsoft Graph Email Client
# ===================================================================

import base64
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional
import msal
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)

class GraphEmailClient:
    """Microsoft Graph API Email Client"""
    
    def __init__(self, client_id: str, client_secret: str, tenant_id: str,
                 from_address: str = None, from_name: str = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.from_address = from_address
        self.from_name = from_name or "Action Plan System"
        
        # MSAL app for authentication
        self.msal_app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=f"https://login.microsoftonline.com/{tenant_id}"
        )
        
        # Graph API endpoints
        self.graph_url = "https://graph.microsoft.com/v1.0"
        self.scopes = ["https://graph.microsoft.com/.default"]
        
        # Token cache
        self._access_token = None
        self._token_expires = None
        
        logger.info("Graph email client initialized", 
                   client_id=client_id, tenant_id=tenant_id)
    
    async def get_access_token(self) -> Optional[str]:
        """Get access token for Graph API"""
        try:
            # Check if we have a valid cached token
            if (self._access_token and self._token_expires and 
                datetime.utcnow() < self._token_expires):
                return self._access_token
            
            # Acquire new token
            result = self.msal_app.acquire_token_for_client(scopes=self.scopes)
            
            if 'access_token' in result:
                self._access_token = result['access_token']
                # Set expiration with 5 minute buffer
                expires_in = result.get('expires_in', 3600)
                self._token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 300)
                
                logger.info("Graph access token acquired")
                return self._access_token
            else:
                error = result.get('error_description', 'Unknown error')
                logger.error("Failed to acquire Graph token", error=error)
                return None
                
        except Exception as e:
            logger.error("Graph token acquisition error", error=str(e))
            return None
    
    async def send_email(self, to_email: str, subject: str, html_content: str,
                        text_content: str = None, attachments: List[Dict] = None) -> bool:
        """Send email via Microsoft Graph API"""
        try:
            # Get access token
            token = await self.get_access_token()
            if not token:
                logger.error("No access token available")
                return False
            
            # Prepare email message
            message = await self._build_message(
                to_email, subject, html_content, text_content, attachments
            )
            
            # Send email
            success = await self._send_graph_message(token, message)
            
            if success:
                logger.info("Email sent via Graph API", to=to_email, subject=subject)
            else:
                logger.error("Graph API email sending failed", to=to_email, subject=subject)
            
            return success
            
        except Exception as e:
            logger.error("Graph email send error", error=str(e), to=to_email, subject=subject)
            return False
    
    async def _build_message(self, to_email: str, subject: str, html_content: str,
                           text_content: str = None, attachments: List[Dict] = None) -> Dict:
        """Build email message for Graph API"""
        try:
            # Basic message structure
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": html_content
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
            
            # Add text content if provided
            if text_content:
                # For Graph API, we can include both HTML and text
                # But we'll prioritize HTML for rich formatting
                pass
            
            # Add attachments
            if attachments:
                message["message"]["attachments"] = []
                for attachment in attachments:
                    graph_attachment = await self._build_attachment(attachment)
                    if graph_attachment:
                        message["message"]["attachments"].append(graph_attachment)
            
            return message
            
        except Exception as e:
            logger.error("Failed to build Graph message", error=str(e))
            return {}
    
    async def _build_attachment(self, attachment: Dict) -> Optional[Dict]:
        """Build attachment for Graph API"""
        try:
            file_path = attachment.get('path')
            file_name = attachment.get('name')
            content_type = attachment.get('content_type', 'application/octet-stream')
            
            if not file_path or not file_name:
                logger.warning("Invalid attachment data", attachment=attachment)
                return None
            
            # Read and encode file
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            
            return {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": file_name,
                "contentType": content_type,
                "contentBytes": encoded_content
            }
            
        except Exception as e:
            logger.error("Failed to build attachment", error=str(e), attachment=attachment)
            return None
    
    async def _send_graph_message(self, token: str, message: Dict) -> bool:
        """Send message via Graph API"""
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.graph_url}/users/{self.from_address}/sendMail"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=message) as response:
                    if response.status == 202:
                        logger.info("Graph API email queued successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error("Graph API error", 
                                   status=response.status, 
                                   error=error_text)
                        return False
                        
        except Exception as e:
            logger.error("Graph API request failed", error=str(e))
            return False
    
    async def test_connection(self) -> bool:
        """Test Graph API connection"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Test with a simple Graph API call
            url = f"{self.graph_url}/me"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        logger.info("Graph API connection test successful")
                        return True
                    else:
                        logger.error("Graph API connection test failed", status=response.status)
                        return False
                        
        except Exception as e:
            logger.error("Graph API connection test error", error=str(e))
            return False
    
    async def get_user_info(self) -> Optional[Dict]:
        """Get user information from Graph API"""
        try:
            token = await self.get_access_token()
            if not token:
                return None
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.graph_url}/users/{self.from_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        return user_data
                    else:
                        logger.error("Failed to get user info", status=response.status)
                        return None
                        
        except Exception as e:
            logger.error("Get user info error", error=str(e))
            return None
    
    def get_connection_info(self) -> Dict:
        """Get connection information"""
        return {
            'client_id': self.client_id,
            'tenant_id': self.tenant_id,
            'from_address': self.from_address,
            'from_name': self.from_name,
            'has_token': bool(self._access_token),
            'token_expires': self._token_expires.isoformat() if self._token_expires else None
        }