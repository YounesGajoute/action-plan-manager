# ===================================================================
# backend/services/onedrive_service.py - OneDrive Sync Service
# ===================================================================

import os
import logging
import tempfile
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import msal
import requests
from flask import current_app

from app.models import Task, SyncStatus, User
from app.services.excel_service import ExcelService
from app import db

logger = logging.getLogger(__name__)

class OneDriveService:
    """Service for OneDrive integration and synchronization"""
    
    def __init__(self):
        self.client_id = current_app.config.get('MS_CLIENT_ID')
        self.client_secret = current_app.config.get('MS_CLIENT_SECRET')
        self.tenant_id = current_app.config.get('MS_TENANT_ID')
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scope = ['https://graph.microsoft.com/.default']
        
        # OneDrive configuration
        self.folder_path = current_app.config.get('ONEDRIVE_FOLDER_PATH', '/Action Plans')
        self.file_name = current_app.config.get('ONEDRIVE_FILE_NAME', 'Plan_daction.xlsx')
        
        # Initialize MSAL client
        self.app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )
    
    def get_access_token(self) -> Optional[str]:
        """Get access token for Microsoft Graph API"""
        try:
            # Try to get token from cache
            accounts = self.app.get_accounts()
            if accounts:
                result = self.app.acquire_token_silent(self.scope, account=accounts[0])
                if result and 'access_token' in result:
                    return result['access_token']
            
            # If no cached token, acquire new one using client credentials
            result = self.app.acquire_token_for_client(scopes=self.scope)
            
            if 'access_token' in result:
                return result['access_token']
            else:
                logger.error(f"Failed to acquire token: {result.get('error_description', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            return None
    
    def get_file_info(self, token: str) -> Optional[Dict]:
        """Get file information from OneDrive"""
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Search for the file in the specified folder
            search_url = f"https://graph.microsoft.com/v1.0/me/drive/root:{self.folder_path}:/children"
            response = requests.get(search_url, headers=headers)
            
            if response.status_code == 200:
                files = response.json().get('value', [])
                for file_item in files:
                    if file_item['name'] == self.file_name:
                        return {
                            'id': file_item['id'],
                            'name': file_item['name'],
                            'size': file_item['size'],
                            'lastModified': file_item['lastModifiedDateTime'],
                            'downloadUrl': file_item.get('@microsoft.graph.downloadUrl'),
                            'webUrl': file_item.get('webUrl')
                        }
                
                logger.warning(f"File {self.file_name} not found in {self.folder_path}")
                return None
            else:
                logger.error(f"Failed to get file info: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return None
    
    def download_file(self, token: str, file_info: Dict) -> Optional[str]:
        """Download file from OneDrive to temporary location"""
        try:
            if not file_info.get('downloadUrl'):
                # Get download URL if not provided
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                
                download_url_endpoint = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_info['id']}/content"
                response = requests.get(download_url_endpoint, headers=headers, allow_redirects=False)
                
                if response.status_code == 302:
                    download_url = response.headers.get('Location')
                else:
                    logger.error(f"Failed to get download URL: {response.status_code}")
                    return None
            else:
                download_url = file_info['downloadUrl']
            
            # Download the file
            response = requests.get(download_url)
            response.raise_for_status()
            
            # Save to temporary file
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_file_path = os.path.join(temp_dir, f"onedrive_sync_{timestamp}.xlsx")
            
            with open(temp_file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded file to: {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return None
    
    def upload_file(self, token: str, local_file_path: str) -> bool:
        """Upload file to OneDrive"""
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/octet-stream'
            }
            
            # Read file content
            with open(local_file_path, 'rb') as f:
                file_content = f.read()
            
            # Upload file
            upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:{self.folder_path}/{self.file_name}:/content"
            response = requests.put(upload_url, headers=headers, data=file_content)
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully uploaded file to OneDrive")
                return True
            else:
                logger.error(f"Failed to upload file: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return False
    
    def sync_from_onedrive(self, user_id: str) -> Dict:
        """Synchronize tasks from OneDrive Excel file"""
        sync_status = SyncStatus(
            sync_type='onedrive_import',
            status='in_progress',
            message='Starting OneDrive sync',
            started_at=datetime.utcnow()
        )
        db.session.add(sync_status)
        db.session.commit()
        
        try:
            # Get access token
            token = self.get_access_token()
            if not token:
                raise Exception("Failed to get access token")
            
            # Get file info
            file_info = self.get_file_info(token)
            if not file_info:
                raise Exception(f"File {self.file_name} not found in OneDrive")
            
            # Check if file has been modified since last sync
            last_sync = SyncStatus.query.filter_by(
                sync_type='onedrive_import',
                status='success'
            ).order_by(SyncStatus.completed_at.desc()).first()
            
            file_modified = datetime.fromisoformat(file_info['lastModified'].replace('Z', '+00:00'))
            
            if last_sync and last_sync.completed_at:
                if file_modified <= last_sync.completed_at:
                    sync_status.status = 'success'
                    sync_status.message = 'No changes detected, sync skipped'
                    sync_status.completed_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"OneDrive sync completed successfully: {import_result['imported']} imported, {import_result['updated']} updated")
            
            return {
                'success': True,
                'message': 'OneDrive sync completed successfully',
                'imported': import_result['imported'],
                'updated': import_result['updated'],
                'errors': import_result.get('errors', [])
            }
            
        except Exception as e:
            sync_status.status = 'error'
            sync_status.message = f"OneDrive sync failed: {str(e)}"
            sync_status.completed_at = datetime.utcnow()
            db.session.commit()
            
            logger.error(f"OneDrive sync failed: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'imported': 0,
                'updated': 0
            }
    
    def sync_to_onedrive(self, user_id: str) -> Dict:
        """Export tasks to OneDrive Excel file"""
        sync_status = SyncStatus(
            sync_type='onedrive_export',
            status='in_progress',
            message='Starting export to OneDrive',
            started_at=datetime.utcnow()
        )
        db.session.add(sync_status)
        db.session.commit()
        
        try:
            # Get access token
            token = self.get_access_token()
            if not token:
                raise Exception("Failed to get access token")
            
            # Get all tasks
            tasks = Task.query.order_by(Task.created_at.desc()).all()
            
            # Create temporary Excel file
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_file_path = os.path.join(temp_dir, f"export_to_onedrive_{timestamp}.xlsx")
            
            # Export to Excel
            export_success = ExcelService.export_to_excel(tasks, temp_file_path)
            if not export_success:
                raise Exception("Failed to create Excel file")
            
            try:
                # Upload to OneDrive
                upload_success = self.upload_file(token, temp_file_path)
                if not upload_success:
                    raise Exception("Failed to upload file to OneDrive")
                
                sync_status.status = 'success'
                sync_status.message = f"Export to OneDrive completed: {len(tasks)} tasks exported"
                sync_status.items_processed = len(tasks)
                sync_status.completed_at = datetime.utcnow()
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            
            db.session.commit()
            
            logger.info(f"Export to OneDrive completed: {len(tasks)} tasks exported")
            
            return {
                'success': True,
                'message': 'Export to OneDrive completed successfully',
                'exported': len(tasks)
            }
            
        except Exception as e:
            sync_status.status = 'error'
            sync_status.message = f"Export to OneDrive failed: {str(e)}"
            sync_status.completed_at = datetime.utcnow()
            db.session.commit()
            
            logger.error(f"Export to OneDrive failed: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'exported': 0
            }
    
    def get_sync_status(self) -> Dict:
        """Get current synchronization status"""
        try:
            # Get latest sync status
            latest_sync = SyncStatus.query.order_by(SyncStatus.started_at.desc()).first()
            
            # Check OneDrive connectivity
            token = self.get_access_token()
            is_online = token is not None
            
            if is_online and token:
                try:
                    file_info = self.get_file_info(token)
                    if file_info:
                        last_modified = datetime.fromisoformat(file_info['lastModified'].replace('Z', '+00:00'))
                    else:
                        last_modified = None
                except:
                    last_modified = None
            else:
                last_modified = None
            
            return {
                'isOnlineSyncActive': is_online,
                'lastSyncTime': latest_sync.completed_at.isoformat() if latest_sync and latest_sync.completed_at else None,
                'syncInProgress': latest_sync.status == 'in_progress' if latest_sync else False,
                'error': latest_sync.message if latest_sync and latest_sync.status == 'error' else None,
                'fileLastModified': last_modified.isoformat() if last_modified else None,
                'nextSyncTime': self._calculate_next_sync_time()
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}")
            return {
                'isOnlineSyncActive': False,
                'lastSyncTime': None,
                'syncInProgress': False,
                'error': str(e),
                'fileLastModified': None,
                'nextSyncTime': None
            }
    
    def _calculate_next_sync_time(self) -> Optional[str]:
        """Calculate next scheduled sync time"""
        try:
            sync_interval = current_app.config.get('SYNC_INTERVAL', 300)  # 5 minutes default
            
            # Get last successful sync
            last_sync = SyncStatus.query.filter_by(
                sync_type='onedrive_import',
                status='success'
            ).order_by(SyncStatus.completed_at.desc()).first()
            
            if last_sync and last_sync.completed_at:
                next_sync = last_sync.completed_at + timedelta(seconds=sync_interval)
                return next_sync.isoformat()
            else:
                # If no previous sync, next sync is now + interval
                next_sync = datetime.utcnow() + timedelta(seconds=sync_interval)
                return next_sync.isoformat()
                
        except Exception as e:
            logger.error(f"Error calculating next sync time: {str(e)}")
            return None
    
    def setup_webhook(self, token: str, webhook_url: str) -> bool:
        """Setup webhook for OneDrive file changes (requires app registration with proper permissions)"""
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Get file info first
            file_info = self.get_file_info(token)
            if not file_info:
                logger.error("Cannot setup webhook: file not found")
                return False
            
            # Create subscription
            subscription_data = {
                "changeType": "updated",
                "notificationUrl": webhook_url,
                "resource": f"/me/drive/items/{file_info['id']}",
                "expirationDateTime": (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
                "clientState": "action-plan-webhook"
            }
            
            response = requests.post(
                "https://graph.microsoft.com/v1.0/subscriptions",
                headers=headers,
                json=subscription_data
            )
            
            if response.status_code == 201:
                subscription = response.json()
                logger.info(f"Webhook created successfully: {subscription['id']}")
                return True
            else:
                logger.error(f"Failed to create webhook: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting up webhook: {str(e)}")
            return False
    
    def handle_webhook_notification(self, notification_data: Dict) -> bool:
        """Handle webhook notification from OneDrive"""
        try:
            # Validate notification
            if notification_data.get('clientState') != 'action-plan-webhook':
                logger.warning("Invalid webhook notification: client state mismatch")
                return False
            
            # Extract change information
            resource = notification_data.get('resource')
            change_type = notification_data.get('changeType')
            
            if change_type == 'updated':
                logger.info(f"OneDrive file updated: {resource}")
                
                # Trigger sync (this could be done asynchronously with Celery)
                # For now, we'll just log it and let the scheduled sync handle it
                logger.info("Scheduling sync due to OneDrive file change")
                
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling webhook notification: {str(e)}")
            return False

class OneDriveScheduler:
    """Scheduler for OneDrive synchronization tasks"""
    
    @staticmethod
    def schedule_periodic_sync():
        """Schedule periodic OneDrive synchronization"""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            
            scheduler = BackgroundScheduler()
            
            # Get sync interval from config
            sync_interval = current_app.config.get('SYNC_INTERVAL', 300)  # 5 minutes
            
            # Schedule the sync job
            scheduler.add_job(
                func=OneDriveScheduler.run_sync,
                trigger=IntervalTrigger(seconds=sync_interval),
                id='onedrive_sync',
                name='OneDrive Synchronization',
                replace_existing=True
            )
            
            scheduler.start()
            logger.info(f"OneDrive sync scheduled every {sync_interval} seconds")
            
        except Exception as e:
            logger.error(f"Error scheduling OneDrive sync: {str(e)}")
    
    @staticmethod
    def run_sync():
        """Run OneDrive synchronization"""
        try:
            with current_app.app_context():
                # Get system user for sync operations
                system_user = User.query.filter_by(email='system@techmac.ma').first()
                if not system_user:
                    # Create system user
                    system_user = User(
                        email='system@techmac.ma',
                        name='System',
                        roles=['admin']
                    )
                    db.session.add(system_user)
                    db.session.commit()
                
                # Run sync
                onedrive_service = OneDriveService()
                result = onedrive_service.sync_from_onedrive(system_user.id)
                
                if result['success']:
                    logger.info(f"Scheduled OneDrive sync completed: {result.get('message', 'Success')}")
                else:
                    logger.error(f"Scheduled OneDrive sync failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error in scheduled OneDrive sync: {str(e)}")

# Initialize scheduler when module is imported
def init_onedrive_scheduler(app):
    """Initialize OneDrive scheduler with Flask app context"""
    with app.app_context():
        if app.config.get('ENABLE_ONEDRIVE_SYNC', False):
            OneDriveScheduler.schedule_periodic_sync() = datetime.utcnow()
                    db.session.commit()
                    
                    return {
                        'success': True,
                        'message': 'No changes detected',
                        'imported': 0,
                        'updated': 0,
                        'skipped': True
                    }
            
            # Download file
            temp_file_path = self.download_file(token, file_info)
            if not temp_file_path:
                raise Exception("Failed to download file from OneDrive")
            
            try:
                # Import from Excel
                import_result = ExcelService.import_from_excel(temp_file_path, user_id)
                
                if import_result['success']:
                    sync_status.status = 'success'
                    sync_status.message = f"OneDrive sync completed: {import_result['imported']} imported, {import_result['updated']} updated"
                    sync_status.items_processed = import_result.get('processed', 0)
                    sync_status.items_imported = import_result['imported']
                    sync_status.items_updated = import_result['updated']
                    sync_status.items_failed = len(import_result.get('errors', []))
                else:
                    raise Exception(f"Excel import failed: {import_result.get('error', 'Unknown error')}")
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            
            sync_status.completed_at