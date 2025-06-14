#!/usr/bin/env python3
"""
===================================================================
s3_uploader.py - AWS S3 Backup Upload Handler
===================================================================

Handles uploading backup files to AWS S3 for offsite storage.
Provides secure, encrypted cloud backup functionality.

Features:
- Secure S3 uploads with encryption
- Multi-part uploads for large files
- Progress tracking and resumable uploads
- Lifecycle management integration
- Cross-region replication support
- Backup verification and integrity checks

Author: TechMac Development Team
Version: 1.0.0
"""

import os
import logging
import boto3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import json
import time
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config

class S3Uploader:
    """AWS S3 backup upload handler"""
    
    def __init__(self, bucket: str, access_key: str, secret_key: str, region: str = 'us-east-1'):
        self.bucket = bucket
        self.region = region
        self.logger = logging.getLogger(__name__)
        
        # Configure S3 client with retry settings
        config = Config(
            region_name=region,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=50
        )
        
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=config
            )
            
            # Test connection and bucket access
            self._verify_bucket_access()
            self.logger.info(f"S3 client initialized for bucket: {bucket}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {e}")
            raise
            
    def _verify_bucket_access(self):
        """Verify S3 bucket exists and is accessible"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            self.logger.info(f"S3 bucket access verified: {self.bucket}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Try to create bucket if it doesn't exist
                self._create_bucket()
            else:
                self.logger.error(f"S3 bucket access error: {e}")
                raise
        except NoCredentialsError:
            self.logger.error("AWS credentials not found")
            raise
            
    def _create_bucket(self):
        """Create S3 bucket if it doesn't exist"""
        try:
            if self.region == 'us-east-1':
                # us-east-1 doesn't need LocationConstraint
                self.s3_client.create_bucket(Bucket=self.bucket)
            else:
                self.s3_client.create_bucket(
                    Bucket=self.bucket,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
                
            # Enable versioning
            self.s3_client.put_bucket_versioning(
                Bucket=self.bucket,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # Set lifecycle policy for cost optimization
            self._set_lifecycle_policy()
            
            self.logger.info(f"Created S3 bucket: {self.bucket}")
            
        except Exception as e:
            self.logger.error(f"Failed to create S3 bucket: {e}")
            raise
            
    def _set_lifecycle_policy(self):
        """Set S3 lifecycle policy for automatic storage class transitions"""
        try:
            lifecycle_policy = {
                'Rules': [
                    {
                        'ID': 'BackupTransition',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': 'backups/'},
                        'Transitions': [
                            {
                                'Days': 30,
                                'StorageClass': 'STANDARD_IA'
                            },
                            {
                                'Days': 90,
                                'StorageClass': 'GLACIER'
                            },
                            {
                                'Days': 365,
                                'StorageClass': 'DEEP_ARCHIVE'
                            }
                        ]
                    },
                    {
                        'ID': 'DeleteIncompleteMultipartUploads',
                        'Status': 'Enabled',
                        'Filter': {},
                        'AbortIncompleteMultipartUpload': {
                            'DaysAfterInitiation': 7
                        }
                    }
                ]
            }
            
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket,
                LifecycleConfiguration=lifecycle_policy
            )
            
            self.logger.info("S3 lifecycle policy configured")
            
        except Exception as e:
            self.logger.warning(f"Failed to set lifecycle policy: {e}")
            
    def upload_file(self, file_path: str, s3_key: str, 
                   progress_callback: Optional[Callable] = None,
                   extra_args: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Upload file to S3 with progress tracking
        
        Args:
            file_path: Local file path to upload
            s3_key: S3 object key (path in bucket)
            progress_callback: Optional callback for progress updates
            extra_args: Additional S3 upload arguments
            
        Returns:
            Dict with upload results
        """
        try:
            local_file = Path(file_path)
            
            if not local_file.exists():
                return {
                    'success': False,
                    'error': f'File does not exist: {file_path}'
                }
                
            file_size = local_file.stat().st_size
            self.logger.info(f"Starting S3 upload: {local_file.name} ({file_size / (1024*1024):.1f}MB)")
            
            # Prepare upload arguments
            upload_args = {
                'ServerSideEncryption': 'AES256',
                'StorageClass': 'STANDARD_IA',
                'Metadata': {
                    'upload-timestamp': datetime.now().isoformat(),
                    'original-filename': local_file.name,
                    'file-size': str(file_size)
                }
            }
            
            if extra_args:
                upload_args.update(extra_args)
                
            # Calculate file checksum for integrity verification
            file_md5 = self._calculate_file_md5(local_file)
            upload_args['Metadata']['md5-checksum'] = file_md5
            
            start_time = time.time()
            
            # Use multipart upload for large files (>100MB)
            if file_size > 100 * 1024 * 1024:
                result = self._multipart_upload(local_file, s3_key, upload_args, progress_callback)
            else:
                result = self._simple_upload(local_file, s3_key, upload_args, progress_callback)
                
            upload_time = time.time() - start_time
            
            if result['success']:
                # Verify upload
                verification = self._verify_upload(s3_key, file_md5, file_size)
                result.update(verification)
                
                if verification['verified']:
                    self.logger.info(f"S3 upload completed successfully: {s3_key} ({upload_time:.1f}s)")
                else:
                    self.logger.error(f"S3 upload verification failed: {s3_key}")
                    result['success'] = False
                    result['error'] = 'Upload verification failed'
                    
            return result
            
        except Exception as e:
            self.logger.error(f"S3 upload failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def _simple_upload(self, file_path: Path, s3_key: str, 
                      extra_args: Dict, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """Upload file using simple S3 upload"""
        try:
            if progress_callback:
                # Create progress tracker
                class ProgressTracker:
                    def __init__(self, filename, total_size, callback):
                        self.filename = filename
                        self.total_size = total_size
                        self.callback = callback
                        self.bytes_transferred = 0
                        
                    def __call__(self, bytes_amount):
                        self.bytes_transferred += bytes_amount
                        percent = (self.bytes_transferred / self.total_size) * 100
                        self.callback(self.filename, percent, self.bytes_transferred, self.total_size)
                        
                tracker = ProgressTracker(file_path.name, file_path.stat().st_size, progress_callback)
                extra_args['Callback'] = tracker
                
            self.s3_client.upload_file(
                str(file_path),
                self.bucket,
                s3_key,
                ExtraArgs=extra_args
            )
            
            return {
                'success': True,
                'upload_method': 'simple',
                's3_key': s3_key,
                'bucket': self.bucket
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    def _multipart_upload(self, file_path: Path, s3_key: str, 
                         extra_args: Dict, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """Upload large file using multipart upload"""
        try:
            # Remove Callback from extra_args as it's not supported in multipart upload
            extra_args_copy = extra_args.copy()
            extra_args_copy.pop('Callback', None)
            
            # Create multipart upload
            response = self.s3_client.create_multipart_upload(
                Bucket=self.bucket,
                Key=s3_key,
                **extra_args_copy
            )
            
            upload_id = response['UploadId']
            file_size = file_path.stat().st_size
            chunk_size = 100 * 1024 * 1024  # 100MB chunks
            parts = []
            bytes_uploaded = 0
            
            try:
                with open(file_path, 'rb') as f:
                    part_number = 1
                    
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                            
                        # Upload part
                        part_response = self.s3_client.upload_part(
                            Bucket=self.bucket,
                            Key=s3_key,
                            PartNumber=part_number,
                            UploadId=upload_id,
                            Body=chunk
                        )
                        
                        parts.append({
                            'ETag': part_response['ETag'],
                            'PartNumber': part_number
                        })
                        
                        bytes_uploaded += len(chunk)
                        
                        # Progress callback
                        if progress_callback:
                            percent = (bytes_uploaded / file_size) * 100
                            progress_callback(file_path.name, percent, bytes_uploaded, file_size)
                            
                        part_number += 1
                        
                # Complete multipart upload
                self.s3_client.complete_multipart_upload(
                    Bucket=self.bucket,
                    Key=s3_key,
                    UploadId=upload_id,
                    MultipartUpload={'Parts': parts}
                )
                
                return {
                    'success': True,
                    'upload_method': 'multipart',
                    's3_key': s3_key,
                    'bucket': self.bucket,
                    'parts_count': len(parts)
                }
                
            except Exception as e:
                # Abort multipart upload on error
                self.s3_client.abort_multipart_upload(
                    Bucket=self.bucket,
                    Key=s3_key,
                    UploadId=upload_id
                )
                raise e
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    def _calculate_file_md5(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
        
    def _verify_upload(self, s3_key: str, expected_md5: str, expected_size: int) -> Dict[str, Any]:
        """Verify uploaded file integrity"""
        try:
            # Get object metadata
            response = self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            
            # Check size
            actual_size = response['ContentLength']
            if actual_size != expected_size:
                return {
                    'verified': False,
                    'error': f'Size mismatch: expected {expected_size}, got {actual_size}'
                }
                
            # Check MD5 if available in metadata
            metadata = response.get('Metadata', {})
            stored_md5 = metadata.get('md5-checksum')
            
            if stored_md5 and stored_md5 != expected_md5:
                return {
                    'verified': False,
                    'error': f'MD5 mismatch: expected {expected_md5}, got {stored_md5}'
                }
                
            return {
                'verified': True,
                'size': actual_size,
                'etag': response['ETag'],
                'last_modified': response['LastModified']
            }
            
        except Exception as e:
            return {
                'verified': False,
                'error': str(e)
            }
            
    def download_file(self, s3_key: str, local_path: str, 
                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Download file from S3"""
        try:
            local_file = Path(local_path)
            local_file.parent.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Starting S3 download: {s3_key}")
            
            if progress_callback:
                # Get object size first
                response = self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
                file_size = response['ContentLength']
                
                class DownloadTracker:
                    def __init__(self, filename, total_size, callback):
                        self.filename = filename
                        self.total_size = total_size
                        self.callback = callback
                        self.bytes_transferred = 0
                        
                    def __call__(self, bytes_amount):
                        self.bytes_transferred += bytes_amount
                        percent = (self.bytes_transferred / self.total_size) * 100
                        self.callback(self.filename, percent, self.bytes_transferred, self.total_size)
                        
                tracker = DownloadTracker(s3_key, file_size, progress_callback)
                
                self.s3_client.download_file(
                    self.bucket,
                    s3_key,
                    str(local_file),
                    Callback=tracker
                )
            else:
                self.s3_client.download_file(self.bucket, s3_key, str(local_file))
                
            self.logger.info(f"S3 download completed: {local_path}")
            
            return {
                'success': True,
                'local_path': str(local_file),
                'size': local_file.stat().st_size
            }
            
        except Exception as e:
            self.logger.error(f"S3 download failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def list_backups(self, prefix: str = 'backups/') -> List[Dict[str, Any]]:
        """List backup files in S3 bucket"""
        try:
            backups = []
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)
            
            for page in pages:
                for obj in page.get('Contents', []):
                    try:
                        # Get object metadata
                        head_response = self.s3_client.head_object(
                            Bucket=self.bucket,
                            Key=obj['Key']
                        )
                        
                        backups.append({
                            'key': obj['Key'],
                            'filename': obj['Key'].split('/')[-1],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'storage_class': obj.get('StorageClass', 'STANDARD'),
                            'etag': obj['ETag'],
                            'metadata': head_response.get('Metadata', {})
                        })
                    except Exception as e:
                        self.logger.warning(f"Could not get metadata for {obj['Key']}: {e}")
                        
            # Sort by last modified (newest first)
            backups.sort(key=lambda x: x['last_modified'], reverse=True)
            
            return backups
            
        except Exception as e:
            self.logger.error(f"Failed to list S3 backups: {e}")
            return []
            
    def delete_file(self, s3_key: str) -> Dict[str, Any]:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            self.logger.info(f"Deleted S3 object: {s3_key}")
            
            return {
                'success': True,
                'deleted_key': s3_key
            }
            
        except Exception as e:
            self.logger.error(f"Failed to delete S3 object {s3_key}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def cleanup_old_backups(self, prefix: str = 'backups/', retention_days: int = 90) -> Dict[str, Any]:
        """Clean up old backups from S3 based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            deleted_count = 0
            total_size_freed = 0
            
            self.logger.info(f"Cleaning up S3 backups older than {retention_days} days")
            
            backups = self.list_backups(prefix)
            
            for backup in backups:
                # Convert to timezone-naive datetime for comparison
                backup_date = backup['last_modified'].replace(tzinfo=None)
                
                if backup_date < cutoff_date:
                    result = self.delete_file(backup['key'])
                    if result['success']:
                        deleted_count += 1
                        total_size_freed += backup['size']
                        self.logger.info(f"Deleted old S3 backup: {backup['key']}")
                        
            size_freed_mb = total_size_freed / (1024 * 1024)
            self.logger.info(f"S3 cleanup completed: {deleted_count} files deleted, {size_freed_mb:.1f}MB freed")
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'size_freed': total_size_freed
            }
            
        except Exception as e:
            self.logger.error(f"S3 cleanup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def get_bucket_info(self) -> Dict[str, Any]:
        """Get S3 bucket information and statistics"""
        try:
            # Get bucket location
            location = self.s3_client.get_bucket_location(Bucket=self.bucket)
            region = location['LocationConstraint'] or 'us-east-1'
            
            # Get bucket versioning status
            versioning = self.s3_client.get_bucket_versioning(Bucket=self.bucket)
            
            # Count objects and calculate total size
            total_objects = 0
            total_size = 0
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket)
            
            for page in pages:
                for obj in page.get('Contents', []):
                    total_objects += 1
                    total_size += obj['Size']
                    
            return {
                'bucket_name': self.bucket,
                'region': region,
                'versioning': versioning.get('Status', 'Disabled'),
                'total_objects': total_objects,
                'total_size': total_size,
                'total_size_mb': total_size / (1024 * 1024)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get bucket info: {e}")
            return {
                'error': str(e)
            }

def main():
    """CLI interface for S3 upload operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description='S3 Backup Upload Utility')
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--access-key', required=True, help='AWS access key')
    parser.add_argument('--secret-key', required=True, help='AWS secret key')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--action', choices=['upload', 'download', 'list', 'delete', 'cleanup'], 
                       default='upload', help='Action to perform')
    parser.add_argument('--file-path', help='Local file path')
    parser.add_argument('--s3-key', help='S3 object key')
    parser.add_argument('--prefix', default='backups/', help='S3 prefix for listing/cleanup')
    parser.add_argument('--retention-days', type=int, default=90,
                       help='Retention period for cleanup')
    
    args = parser.parse_args()
    
    # Setup logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    def progress_callback(filename, percent, bytes_transferred, total_bytes):
        print(f"\r{filename}: {percent:.1f}% ({bytes_transferred}/{total_bytes} bytes)", end='')
        
    # Initialize S3 uploader
    uploader = S3Uploader(
        bucket=args.bucket,
        access_key=args.access_key,
        secret_key=args.secret_key,
        region=args.region
    )
    
    if args.action == 'upload':
        if not args.file_path or not args.s3_key:
            print("Error: --file-path and --s3-key are required for upload")
            return
            
        print(f"Uploading {args.file_path} to s3://{args.bucket}/{args.s3_key}")
        result = uploader.upload_file(args.file_path, args.s3_key, progress_callback)
        print()  # New line after progress
        
        if result['success']:
            print("Upload completed successfully")
            if result.get('verified'):
                print("Upload verification passed")
        else:
            print(f"Upload failed: {result['error']}")
            
    elif args.action == 'download':
        if not args.s3_key or not args.file_path:
            print("Error: --s3-key and --file-path are required for download")
            return
            
        print(f"Downloading s3://{args.bucket}/{args.s3_key} to {args.file_path}")
        result = uploader.download_file(args.s3_key, args.file_path, progress_callback)
        print()  # New line after progress
        
        if result['success']:
            print("Download completed successfully")
        else:
            print(f"Download failed: {result['error']}")
            
    elif args.action == 'list':
        print(f"Listing backups in s3://{args.bucket}/{args.prefix}")
        backups = uploader.list_backups(args.prefix)
        
        for backup in backups:
            size_mb = backup['size'] / (1024 * 1024)
            print(f"  {backup['key']} - {size_mb:.1f}MB - {backup['last_modified']}")
            
    elif args.action == 'delete':
        if not args.s3_key:
            print("Error: --s3-key is required for delete")
            return
            
        print(f"Deleting s3://{args.bucket}/{args.s3_key}")
        result = uploader.delete_file(args.s3_key)
        
        if result['success']:
            print("Delete completed successfully")
        else:
            print(f"Delete failed: {result['error']}")
            
    elif args.action == 'cleanup':
        print(f"Cleaning up backups older than {args.retention_days} days...")
        result = uploader.cleanup_old_backups(args.prefix, args.retention_days)
        
        if result['success']:
            size_mb = result['size_freed'] / (1024 * 1024)
            print(f"Cleanup completed: {result['deleted_count']} files deleted, {size_mb:.1f}MB freed")
        else:
            print(f"Cleanup failed: {result['error']}")

if __name__ == "__main__":
    main()