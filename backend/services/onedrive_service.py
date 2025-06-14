#!/usr/bin/env python3
# ===================================================================
# backend/services/onedrive_service.py - Enhanced OneDrive Service
# ===================================================================

import os
import logging
import tempfile
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import msal
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import current_app
import threading
import time

from app.models import Task, SyncStatus, User, SyncConflict
from app.services.excel_service import ExcelService
from app.services.notification_service import NotificationService
from app import db

logger = logging.getLogger(__name__)

class TokenManager:
    """Thread-safe token management"""
    
    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.scope = ['https://graph.microsoft.com/.default']
        self._lock = threading.Lock()
        self._token_cache = {}
        
        # Initialize MSAL client
        self.app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )
        
    def get_token(self, user_id: str = None) -> Optional[str]:
        """Get valid access token with automatic refresh"""
        with self._lock:
            cache_key = user_id or 'app_token'
            
            # Check if we have a cached valid token
            if cache_key in self._token_cache:
                token_info = self._token_cache[cache_key]
                if datetime.utcnow() < token_info['expires_at']:
                    return token_info['access_token']
                    
            # Acquire new token
            try:
                if user_id:
                    # User-specific token (delegated permissions)
                    user = User.query.get(user_id)
                    if user and user.refresh_token:
                        result = self.app.acquire_token_by_refresh_token(
                            user.refresh_token,
                            scopes=self.scope
                        )
                    else:
                        return None
                else:
                    # Application token (application permissions)
                    result = self.app.acquire_token_for_client(scopes=self.scope)
                    
                if 'access_token' in result:
                    expires_in = result.get('expires_in', 3600)
                    expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)  # 5 min buffer
                    
                    self._token_cache[cache_key] = {
                        'access_token': result['access_token'],
                        'expires_at': expires_at
                    }
                    
                    # Update refresh token if provided
                    if user_id and 'refresh_token' in result:
                        user = User.query.get(user_id)
                        if user:
                            user.refresh_token = result['refresh_token']
                            db.session.commit()
                            
                    logger.info(f"Successfully acquired token for {cache_key}")
                    return result['access_token']
                else:
                    logger.error(f"Failed to acquire token: {result.get('error_description', 'Unknown error')}")
                    return None
                    
            except Exception as e:
                logger.error(f"Token acquisition error: {str(e)}")
                return None

class OneDriveClient:
    """Enhanced OneDrive client with retry logic and better error handling"""
    
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self.base_url = "https://graph.microsoft.com/v1.0"
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            respect_retry_after_header=True
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    def _make_request(self, method: str, url: str, user_id: str = None, **kwargs) -> requests.Response:
        """Make authenticated request with proper error handling"""
        token = self.token_manager.get_token(user_id)
        if not token:
            raise Exception("Failed to get access token")
            
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {token}'
        kwargs['headers'] = headers
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited, waiting {retry_after} seconds")
                time.sleep(retry_after)
                return self._make_request(method, url, user_id, **kwargs)
                
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {method} {url} - {str(e)}")
            raise
            
    def get_file_info(self, file_path: str, user_id: str = None) -> Optional[Dict]:
        """Get file information from OneDrive"""
        try:
            encoded_path = requests.utils.quote(file_path, safe='/')
            url = f"{self.base_url}/me/drive/root:/{encoded_path}"
            
            response = self._make_request('GET', url, user_id)
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"File not found: {file_path}")
                return None
            raise
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return None
            
    def download_file(self, file_path: str, local_path: str, user_id: str = None) -> bool:
        """Download file from OneDrive"""
        try:
            file_info = self.get_file_info(file_path, user_id)
            if not file_info:
                return False
                
            # Get download URL
            download_url = file_info.get('@microsoft.graph.downloadUrl')
            if not download_url:
                # Request download URL for large files
                encoded_path = requests.utils.quote(file_path, safe='/')
                content_url = f"{self.base_url}/me/drive/root:/{encoded_path}:/content"
                response = self._make_request('GET', content_url, user_id)
                download_url = response.url
                
            # Download file
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            logger.info(f"Downloaded file: {file_path} -> {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return False
            
    def upload_file(self, local_path: str, remote_path: str, user_id: str = None) -> bool:
        """Upload file to OneDrive with chunked upload for large files"""
        try:
            file_size = os.path.getsize(local_path)
            
            if file_size < 4 * 1024 * 1024:  # 4MB threshold
                return self._simple_upload(local_path, remote_path, user_id)
            else:
                return self._chunked_upload(local_path, remote_path, user_id)
                
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return False
            
    def _simple_upload(self, local_path: str, remote_path: str, user_id: str = None) -> bool:
        """Simple upload for small files"""
        try:
            encoded_path = requests.utils.quote(remote_path, safe='/')
            url = f"{self.base_url}/me/drive/root:/{encoded_path}:/content"
            
            with open(local_path, 'rb') as f:
                response = self._make_request('PUT', url, user_id, data=f)
                
            logger.info(f"Uploaded file: {local_path} -> {remote_path}")
            return True
            
        except Exception as e:
            logger.error(f"Simple upload failed: {str(e)}")
            return False
            
    def _chunked_upload(self, local_path: str, remote_path: str, user_id: str = None) -> bool:
        """Chunked upload for large files"""
        try:
            file_size = os.path.getsize(local_path)
            chunk_size = 5 * 1024 * 1024  # 5MB chunks
            
            # Create upload session
            encoded_path = requests.utils.quote(remote_path, safe='/')
            session_url = f"{self.base_url}/me/drive/root:/{encoded_path}:/createUploadSession"
            
            session_data = {
                "item": {
                    "@microsoft.graph.conflictBehavior": "replace",
                    "name": os.path.basename(remote_path)
                }
            }
            
            response = self._make_request('POST', session_url, user_id, json=session_data)
            upload_url = response.json()['uploadUrl']
            
            # Upload chunks
            with open(local_path, 'rb') as f:
                chunk_start = 0
                
                while chunk_start < file_size:
                    chunk_end = min(chunk_start + chunk_size - 1, file_size - 1)
                    chunk_data = f.read(chunk_size)
                    
                    headers = {
                        'Content-Range': f'bytes {chunk_start}-{chunk_end}/{file_size}',
                        'Content-Length': str(len(chunk_data))
                    }
                    
                    response = requests.put(upload_url, headers=headers, data=chunk_data)
                    response.raise_for_status()
                    
                    chunk_start = chunk_end + 1
                    
                    # Log progress
                    progress = (chunk_start / file_size) * 100
                    logger.info(f"Upload progress: {progress:.1f}%")
                    
            logger.info(f"Chunked upload completed: {local_path} -> {remote_path}")
            return True
            
        except Exception as e:
            logger.error(f"Chunked upload failed: {str(e)}")
            return False
            
    def list_files(self, folder_path: str = "", user_id: str = None) -> List[Dict]:
        """List files in OneDrive folder"""
        try:
            if folder_path:
                encoded_path = requests.utils.quote(folder_path, safe='/')
                url = f"{self.base_url}/me/drive/root:/{encoded_path}:/children"
            else:
                url = f"{self.base_url}/me/drive/root/children"
                
            response = self._make_request('GET', url, user_id)
            return response.json().get('value', [])
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []
            
    def delete_file(self, file_path: str, user_id: str = None) -> bool:
        """Delete file from OneDrive"""
        try:
            encoded_path = requests.utils.quote(file_path, safe='/')
            url = f"{self.base_url}/me/drive/root:/{encoded_path}"
            
            response = self._make_request('DELETE', url, user_id)
            logger.info(f"Deleted file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False

class ConflictResolver:
    """Handle sync conflicts between local and OneDrive data"""
    
    @staticmethod
    def detect_conflicts(local_tasks: List[Task], remote_data: List[Dict]) -> List[Dict]:
        """Detect conflicts between local and remote data"""
        conflicts = []
        
        # Create lookup dictionaries
        local_by_po = {task.po_number: task for task in local_tasks if task.po_number}
        remote_by_po = {item.get('po_number'): item for item in remote_data if item.get('po_number')}
        
        # Check for conflicts
        for po_number in set(local_by_po.keys()) & set(remote_by_po.keys()):
            local_task = local_by_po[po_number]
            remote_item = remote_by_po[po_number]
            
            # Compare modification times
            local_modified = local_task.updated_at
            remote_modified = datetime.fromisoformat(remote_item.get('last_modified', '1970-01-01'))
            
            # Check if data differs
            if ConflictResolver._tasks_differ(local_task, remote_item):
                conflicts.append({
                    'po_number': po_number,
                    'local_task': local_task,
                    'remote_item': remote_item,
                    'local_modified': local_modified,
                    'remote_modified': remote_modified,
                    'conflict_type': ConflictResolver._determine_conflict_type(local_modified, remote_modified)
                })
                
        return conflicts
        
    @staticmethod
    def _tasks_differ(local_task: Task, remote_item: Dict) -> bool:
        """Check if local and remote tasks have different data"""
        fields_to_compare = [
            'action_description', 'customer', 'requester', 'responsible',
            'status', 'category', 'notes'
        ]
        
        for field in fields_to_compare:
            local_value = getattr(local_task, field, None)
            remote_value = remote_item.get(field)
            
            if str(local_value or '').strip() != str(remote_value or '').strip():
                return True
                
        return False
        
    @staticmethod
    def _determine_conflict_type(local_modified: datetime, remote_modified: datetime) -> str:
        """Determine type of conflict"""
        time_diff = abs((local_modified - remote_modified).total_seconds())
        
        if time_diff < 60:  # Less than 1 minute difference
            return 'simultaneous'
        elif local_modified > remote_modified:
            return 'local_newer'
        else:
            return 'remote_newer'
            
    @staticmethod
    def resolve_conflict(conflict: Dict, resolution_strategy: str) -> Dict:
        """Resolve conflict based on strategy"""
        if resolution_strategy == 'local_wins':
            return {'action': 'keep_local', 'data': conflict['local_task']}
        elif resolution_strategy == 'remote_wins':
            return {'action': 'use_remote', 'data': conflict['remote_item']}
        elif resolution_strategy == 'newest_wins':
            if conflict['conflict_type'] == 'local_newer':
                return {'action': 'keep_local', 'data': conflict['local_task']}
            else:
                return {'action': 'use_remote', 'data': conflict['remote_item']}
        elif resolution_strategy == 'manual':
            return {'action': 'manual_review', 'conflict': conflict}
        else:
            return {'action': 'skip', 'reason': 'unknown_strategy'}

class OneDriveService:
    """Enhanced OneDrive service with comprehensive sync capabilities"""
    
    def __init__(self):
        self.client_id = current_app.config.get('MS_CLIENT_ID')
        self.client_secret = current_app.config.get('MS_CLIENT_SECRET')
        self.tenant_id = current_app.config.get('MS_TENANT_ID')
        
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            raise ValueError("Microsoft 365 credentials not properly configured")
            
        # OneDrive configuration
        self.folder_path = current_app.config.get('ONEDRIVE_FOLDER_PATH', '/Action Plans')
        self.file_name = current_app.config.get('ONEDRIVE_FILE_NAME', 'Plan_daction.xlsx')
        self.full_path = f"{self.folder_path.rstrip('/')}/{self.file_name}"
        
        # Sync configuration
        self.conflict_resolution = current_app.config.get('SYNC_CONFLICT_RESOLUTION', 'newest_wins')
        self.sync_enabled = current_app.config.get('ENABLE_ONEDRIVE_SYNC', True)
        
        # Initialize components
        self.token_manager = TokenManager(self.client_id, self.client_secret, self.tenant_id)
        self.client = OneDriveClient(self.token_manager)
        self.conflict_resolver = ConflictResolver()
        
    def test_connection(self, user_id: str = None) -> Dict[str, Any]:
        """Test OneDrive connection and permissions"""
        try:
            token = self.token_manager.get_token(user_id)
            if not token:
                return {'success': False, 'error': 'Failed to get access token'}
                
            # Test basic connectivity
            response = self.client._make_request('GET', f"{self.client.base_url}/me/drive", user_id)
            drive_info = response.json()
            
            # Test folder access
            folder_exists = self.client.get_file_info(self.folder_path.lstrip('/'), user_id) is not None
            
            return {
                'success': True,
                'drive_name': drive_info.get('name'),
                'drive_type': drive_info.get('driveType'),
                'quota_total': drive_info.get('quota', {}).get('total'),
                'quota_used': drive_info.get('quota', {}).get('used'),
                'folder_exists': folder_exists,
                'folder_path': self.folder_path,
                'file_name': self.file_name
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def sync_from_onedrive(self, user_id: str, force: bool = False) -> Dict[str, Any]:
        """Synchronize tasks from OneDrive Excel file"""
        sync_status = SyncStatus(
            sync_type='onedrive_import',
            status='in_progress',
            message='Starting OneDrive import sync',
            started_at=datetime.utcnow(),
            user_id=user_id
        )
        db.session.add(sync_status)
        db.session.commit()
        
        try:
            if not self.sync_enabled and not force:
                raise Exception("OneDrive sync is disabled")
                
            logger.info(f"Starting OneDrive import sync for user {user_id}")
            
            # Check for existing file
            file_info = self.client.get_file_info(self.full_path.lstrip('/'), user_id)
            if not file_info:
                raise Exception(f"File {self.full_path} not found in OneDrive")
                
            # Check if file has been modified since last sync
            if not force:
                last_sync = SyncStatus.query.filter_by(
                    sync_type='onedrive_import',
                    status='success',
                    user_id=user_id
                ).order_by(SyncStatus.completed_at.desc()).first()
                
                if last_sync and last_sync.completed_at:
                    file_modified = datetime.fromisoformat(
                        file_info['lastModifiedDateTime'].replace('Z', '+00:00')
                    ).replace(tzinfo=None)
                    
                    if file_modified <= last_sync.completed_at:
                        sync_status.status = 'success'
                        sync_status.message = 'No changes detected, sync skipped'
                        sync_status.completed_at = datetime.utcnow()
                        db.session.commit()
                        
                        return {
                            'success': True,
                            'message': 'No changes detected',
                            'imported': 0,
                            'updated': 0,
                            'conflicts': 0,
                            'skipped': True
                        }
                        
            # Download file
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
                temp_path = temp_file.name
                
            try:
                download_success = self.client.download_file(self.full_path.lstrip('/'), temp_path, user_id)
                if not download_success:
                    raise Exception("Failed to download file from OneDrive")
                    
                # Parse Excel file
                remote_data = ExcelService.parse_excel_file(temp_path)
                if not remote_data:
                    raise Exception("Failed to parse downloaded Excel file")
                    
                # Get current local tasks
                local_tasks = Task.query.all()
                
                # Detect conflicts
                conflicts = self.conflict_resolver.detect_conflicts(local_tasks, remote_data)
                
                # Process conflicts
                conflict_resolutions = []
                for conflict in conflicts:
                    resolution = self.conflict_resolver.resolve_conflict(conflict, self.conflict_resolution)
                    conflict_resolutions.append(resolution)
                    
                    # Store conflict for manual review if needed
                    if resolution['action'] == 'manual_review':
                        conflict_record = SyncConflict(
                            po_number=conflict['po_number'],
                            local_data=json.dumps(self._task_to_dict(conflict['local_task'])),
                            remote_data=json.dumps(conflict['remote_item']),
                            conflict_type=conflict['conflict_type'],
                            status='pending',
                            created_at=datetime.utcnow()
                        )
                        db.session.add(conflict_record)
                        
                # Import/update tasks
                import_result = ExcelService.import_from_data(
                    remote_data, 
                    conflict_resolutions=conflict_resolutions
                )
                
                sync_status.status = 'success'
                sync_status.message = f"OneDrive import completed: {import_result['imported']} imported, {import_result['updated']} updated, {len(conflicts)} conflicts"
                sync_status.items_processed = len(remote_data)
                sync_status.completed_at = datetime.utcnow()
                
                db.session.commit()
                
                logger.info(f"OneDrive import sync completed: {import_result}")
                
                # Send notification
                if current_app.config.get('ENABLE_EMAIL_NOTIFICATIONS'):
                    NotificationService.send_sync_notification(
                        user_id, 'onedrive_import', import_result
                    )
                    
                return {
                    'success': True,
                    'message': 'OneDrive import completed successfully',
                    'imported': import_result['imported'],
                    'updated': import_result['updated'],
                    'conflicts': len(conflicts),
                    'errors': import_result.get('errors', []),
                    'skipped': False
                }
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            sync_status.status = 'error'
            sync_status.message = f"OneDrive import failed: {str(e)}"
            sync_status.completed_at = datetime.utcnow()
            db.session.commit()
            
            logger.error(f"OneDrive import sync failed: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'imported': 0,
                'updated': 0,
                'conflicts': 0
            }
            
    def sync_to_onedrive(self, user_id: str, force: bool = False) -> Dict[str, Any]:
        """Export tasks to OneDrive Excel file"""
        sync_status = SyncStatus(
            sync_type='onedrive_export',
            status='in_progress',
            message='Starting OneDrive export sync',
            started_at=datetime.utcnow(),
            user_id=user_id
        )
        db.session.add(sync_status)
        db.session.commit()
        
        try:
            if not self.sync_enabled and not force:
                raise Exception("OneDrive sync is disabled")
                
            logger.info(f"Starting OneDrive export sync for user {user_id}")
            
            # Get all tasks
            tasks = Task.query.order_by(Task.created_at.desc()).all()
            
            # Create temporary Excel file
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
                temp_path = temp_file.name
                
            try:
                # Export to Excel
                export_success = ExcelService.export_to_excel(tasks, temp_path)
                if not export_success:
                    raise Exception("Failed to create Excel file")
                    
                # Upload to OneDrive
                upload_success = self.client.upload_file(temp_path, self.full_path.lstrip('/'), user_id)
                if not upload_success:
                    raise Exception("Failed to upload file to OneDrive")
                    
                sync_status.status = 'success'
                sync_status.message = f"OneDrive export completed: {len(tasks)} tasks exported"
                sync_status.items_processed = len(tasks)
                sync_status.completed_at = datetime.utcnow()
                
                db.session.commit()
                
                logger.info(f"OneDrive export sync completed: {len(tasks)} tasks exported")
                
                # Send notification
                if current_app.config.get('ENABLE_EMAIL_NOTIFICATIONS'):
                    NotificationService.send_sync_notification(
                        user_id, 'onedrive_export', {'exported': len(tasks)}
                    )
                    
                return {
                    'success': True,
                    'message': 'OneDrive export completed successfully',
                    'exported': len(tasks)
                }
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            sync_status.status = 'error'
            sync_status.message = f"OneDrive export failed: {str(e)}"
            sync_status.completed_at = datetime.utcnow()
            db.session.commit()
            
            logger.error(f"OneDrive export sync failed: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'exported': 0
            }
            
    def get_sync_status(self, user_id: str = None) -> Dict[str, Any]:
        """Get current synchronization status"""
        try:
            query = SyncStatus.query
            if user_id:
                query = query.filter_by(user_id=user_id)
                
            latest_import = query.filter_by(sync_type='onedrive_import').order_by(
                SyncStatus.started_at.desc()
            ).first()
            
            latest_export = query.filter_by(sync_type='onedrive_export').order_by(
                SyncStatus.started_at.desc()
            ).first()
            
            # Get pending conflicts
            pending_conflicts = SyncConflict.query.filter_by(status='pending').count()
            
            return {
                'sync_enabled': self.sync_enabled,
                'latest_import': {
                    'status': latest_import.status if latest_import else None,
                    'message': latest_import.message if latest_import else None,
                    'started_at': latest_import.started_at.isoformat() if latest_import else None,
                    'completed_at': latest_import.completed_at.isoformat() if latest_import and latest_import.completed_at else None
                },
                'latest_export': {
                    'status': latest_export.status if latest_export else None,
                    'message': latest_export.message if latest_export else None,
                    'started_at': latest_export.started_at.isoformat() if latest_export else None,
                    'completed_at': latest_export.completed_at.isoformat() if latest_export and latest_export.completed_at else None
                },
                'pending_conflicts': pending_conflicts,
                'folder_path': self.folder_path,
                'file_name': self.file_name
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}")
            return {
                'error': str(e),
                'sync_enabled': False
            }
            
    def resolve_conflicts(self, user_id: str, resolutions: List[Dict]) -> Dict[str, Any]:
        """Resolve pending conflicts"""
        try:
            resolved_count = 0
            errors = []
            
            for resolution in resolutions:
                try:
                    conflict_id = resolution.get('conflict_id')
                    action = resolution.get('action')  # 'use_local', 'use_remote', 'merge'
                    
                    conflict = SyncConflict.query.get(conflict_id)
                    if not conflict:
                        errors.append(f"Conflict {conflict_id} not found")
                        continue
                        
                    if action == 'use_local':
                        # Keep local version, mark conflict as resolved
                        conflict.status = 'resolved_local'
                        conflict.resolved_at = datetime.utcnow()
                        conflict.resolved_by = user_id
                        
                    elif action == 'use_remote':
                        # Apply remote changes
                        remote_data = json.loads(conflict.remote_data)
                        task = Task.query.filter_by(po_number=conflict.po_number).first()
                        
                        if task:
                            for key, value in remote_data.items():
                                if hasattr(task, key):
                                    setattr(task, key, value)
                            task.updated_at = datetime.utcnow()
                            
                        conflict.status = 'resolved_remote'
                        conflict.resolved_at = datetime.utcnow()
                        conflict.resolved_by = user_id
                        
                    elif action == 'merge':
                        # Apply custom merge data if provided
                        merge_data = resolution.get('merge_data', {})
                        task = Task.query.filter_by(po_number=conflict.po_number).first()
                        
                        if task and merge_data:
                            for key, value in merge_data.items():
                                if hasattr(task, key):
                                    setattr(task, key, value)
                            task.updated_at = datetime.utcnow()
                            
                        conflict.status = 'resolved_merged'
                        conflict.resolved_at = datetime.utcnow()
                        conflict.resolved_by = user_id
                        
                    resolved_count += 1
                    
                except Exception as e:
                    errors.append(f"Error resolving conflict {resolution.get('conflict_id')}: {str(e)}")
                    
            db.session.commit()
            
            return {
                'success': True,
                'resolved_count': resolved_count,
                'errors': errors
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error resolving conflicts: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'resolved_count': 0
            }
            
    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert task object to dictionary"""
        return {
            'id': task.id,
            'po_number': task.po_number,
            'action_description': task.action_description,
            'customer': task.customer,
            'requester': task.requester,
            'responsible': task.responsible,
            'status': task.status,
            'category': task.category,
            'notes': task.notes,
            'date': task.date.isoformat() if task.date else None,
            'deadline': task.deadline.isoformat() if task.deadline else None,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'updated_at': task.updated_at.isoformat() if task.updated_at else None
        }
        
    def schedule_sync(self, sync_type: str, user_id: str, interval_minutes: int = 30) -> bool:
        """Schedule automatic synchronization"""
        try:
            from app.tasks.sync_tasks import schedule_onedrive_sync
            
            schedule_onedrive_sync.apply_async(
                args=[sync_type, user_id],
                countdown=interval_minutes * 60
            )
            
            logger.info(f"Scheduled {sync_type} sync for user {user_id} in {interval_minutes} minutes")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling sync: {str(e)}")
            return False

# Utility functions for external use
def get_onedrive_service() -> OneDriveService:
    """Get OneDrive service instance"""
    return OneDriveService()

def test_onedrive_connection(user_id: str = None) -> Dict[str, Any]:
    """Test OneDrive connection"""
    service = get_onedrive_service()
    return service.test_connection(user_id)

def sync_from_onedrive(user_id: str, force: bool = False) -> Dict[str, Any]:
    """Sync from OneDrive"""
    service = get_onedrive_service()
    return service.sync_from_onedrive(user_id, force)

def sync_to_onedrive(user_id: str, force: bool = False) -> Dict[str, Any]:
    """Sync to OneDrive"""
    service = get_onedrive_service()
    return service.sync_to_onedrive(user_id, force)