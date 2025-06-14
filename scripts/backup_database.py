#!/usr/bin/env python3
# ===================================================================
# scripts/backup_database.py - Comprehensive Database Backup Script
# ===================================================================

import os
import sys
import logging
import argparse
import subprocess
import gzip
import shutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import hashlib
import boto3
from azure.storage.blob import BlobServiceClient
import psycopg2
from cryptography.fernet import Fernet

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import BackupLog
from app.services.notification_service import NotificationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DatabaseBackup:
    """Comprehensive database backup system with encryption and cloud storage"""
    
    def __init__(self):
        self.app = create_app()
        self.config = self.app.config
        
        # Backup configuration
        self.backup_dir = Path(os.getenv('BACKUP_DIR', 'backups/database'))
        self.retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
        self.compression = os.getenv('BACKUP_COMPRESSION', 'gzip').lower()
        self.encryption_enabled = os.getenv('BACKUP_ENCRYPTION', 'true').lower() == 'true'
        
        # Database configuration
        self.db_url = self.config.get('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not configured")
            
        self.db_config = self._parse_db_url(self.db_url)
        
        # Cloud storage configuration
        self.aws_enabled = bool(os.getenv('AWS_ACCESS_KEY_ID'))
        self.azure_enabled = bool(os.getenv('AZURE_STORAGE_CONNECTION_STRING'))
        
        # Encryption setup
        if self.encryption_enabled:
            encryption_key = os.getenv('BACKUP_ENCRYPTION_KEY')
            if encryption_key:
                self.cipher = Fernet(encryption_key.encode())
            else:
                # Generate new key if not provided
                key = Fernet.generate_key()
                self.cipher = Fernet(key)
                logger.info("Backup encrypted successfully")
                
            # Calculate checksum
            backup_info['checksum'] = self._calculate_checksum(backup_path)
            
            # Upload to cloud storage
            if self.aws_enabled or self.azure_enabled:
                try:
                    cloud_success = self._upload_to_cloud(backup_path, backup_info)
                    backup_info['cloud_uploaded'] = cloud_success
                except Exception as e:
                    logger.warning(f"Cloud upload failed: {str(e)}")
                    
            # Create metadata file
            metadata_path = backup_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(backup_info, f, indent=2, default=str)
                
            backup_info['success'] = True
            backup_info['end_time'] = datetime.utcnow()
            backup_info['duration_seconds'] = (backup_info['end_time'] - start_time).total_seconds()
            
            logger.info(f"Backup completed successfully in {backup_info['duration_seconds']:.2f} seconds")
            
            # Log to database
            self._log_backup(backup_info)
            
            return backup_info
            
        except Exception as e:
            backup_info['error'] = str(e)
            backup_info['end_time'] = datetime.utcnow()
            backup_info['duration_seconds'] = (backup_info['end_time'] - start_time).total_seconds()
            
            logger.error(f"Backup failed: {str(e)}")
            
            # Clean up failed backup file
            if backup_path.exists():
                backup_path.unlink()
                
            # Log failed backup
            self._log_backup(backup_info)
            
            return backup_info
            
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
        
    def _upload_to_cloud(self, backup_path: Path, backup_info: Dict) -> bool:
        """Upload backup to cloud storage"""
        success = False
        
        # Upload to AWS S3
        if self.aws_enabled:
            try:
                s3_client = boto3.client('s3')
                bucket = os.getenv('BACKUP_S3_BUCKET')
                
                if bucket:
                    s3_key = f"database-backups/{backup_info['filename']}"
                    
                    logger.info(f"Uploading to S3: s3://{bucket}/{s3_key}")
                    s3_client.upload_file(
                        str(backup_path),
                        bucket,
                        s3_key,
                        ExtraArgs={
                            'Metadata': {
                                'backup-type': backup_info['type'],
                                'timestamp': backup_info['timestamp'],
                                'checksum': backup_info.get('checksum', ''),
                                'database': self.db_config['database']
                            }
                        }
                    )
                    
                    backup_info['s3_location'] = f"s3://{bucket}/{s3_key}"
                    logger.info("S3 upload completed")
                    success = True
                    
            except Exception as e:
                logger.error(f"S3 upload failed: {str(e)}")
                
        # Upload to Azure Blob Storage
        if self.azure_enabled:
            try:
                connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
                container_name = os.getenv('AZURE_BACKUP_CONTAINER', 'database-backups')
                
                blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                blob_name = f"database-backups/{backup_info['filename']}"
                
                logger.info(f"Uploading to Azure Blob: {blob_name}")
                
                with open(backup_path, 'rb') as data:
                    blob_service_client.get_blob_client(
                        container=container_name,
                        blob=blob_name
                    ).upload_blob(data, overwrite=True)
                    
                backup_info['azure_location'] = f"azure://{container_name}/{blob_name}"
                logger.info("Azure Blob upload completed")
                success = True
                
            except Exception as e:
                logger.error(f"Azure Blob upload failed: {str(e)}")
                
        return success
        
    def _log_backup(self, backup_info: Dict) -> None:
        """Log backup to database"""
        try:
            with self.app.app_context():
                backup_log = BackupLog(
                    filename=backup_info['filename'],
                    backup_type=backup_info['type'],
                    size_bytes=backup_info['size_bytes'],
                    compressed_size_bytes=backup_info.get('compressed_size_bytes', 0),
                    success=backup_info['success'],
                    error_message=backup_info.get('error'),
                    duration_seconds=backup_info.get('duration_seconds', 0),
                    checksum=backup_info.get('checksum'),
                    cloud_uploaded=backup_info.get('cloud_uploaded', False),
                    encrypted=backup_info.get('encrypted', False),
                    created_at=backup_info['start_time']
                )
                
                from app import db
                db.session.add(backup_log)
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Failed to log backup to database: {str(e)}")
            
    def cleanup_old_backups(self) -> Dict[str, int]:
        """Clean up old backup files based on retention policy"""
        logger.info(f"Cleaning up backups older than {self.retention_days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        deleted_local = 0
        deleted_cloud = 0
        errors = []
        
        try:
            # Clean up local files
            for backup_file in self.backup_dir.glob('actionplan_backup_*'):
                try:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        backup_file.unlink()
                        deleted_local += 1
                        logger.info(f"Deleted old backup: {backup_file.name}")
                        
                        # Also delete metadata file if exists
                        metadata_file = backup_file.with_suffix('.json')
                        if metadata_file.exists():
                            metadata_file.unlink()
                            
                except Exception as e:
                    errors.append(f"Failed to delete {backup_file.name}: {str(e)}")
                    
            # Clean up cloud storage
            if self.aws_enabled:
                deleted_cloud += self._cleanup_s3_backups(cutoff_date)
                
            if self.azure_enabled:
                deleted_cloud += self._cleanup_azure_backups(cutoff_date)
                
            logger.info(f"Cleanup completed: {deleted_local} local files, {deleted_cloud} cloud files deleted")
            
            return {
                'deleted_local': deleted_local,
                'deleted_cloud': deleted_cloud,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return {
                'deleted_local': deleted_local,
                'deleted_cloud': deleted_cloud,
                'errors': errors + [str(e)]
            }
            
    def _cleanup_s3_backups(self, cutoff_date: datetime) -> int:
        """Clean up old S3 backups"""
        deleted = 0
        try:
            s3_client = boto3.client('s3')
            bucket = os.getenv('BACKUP_S3_BUCKET')
            
            if not bucket:
                return 0
                
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix='database-backups/'
            )
            
            for obj in response.get('Contents', []):
                if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                    s3_client.delete_object(Bucket=bucket, Key=obj['Key'])
                    deleted += 1
                    logger.info(f"Deleted old S3 backup: {obj['Key']}")
                    
        except Exception as e:
            logger.error(f"S3 cleanup failed: {str(e)}")
            
        return deleted
        
    def _cleanup_azure_backups(self, cutoff_date: datetime) -> int:
        """Clean up old Azure backups"""
        deleted = 0
        try:
            connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            container_name = os.getenv('AZURE_BACKUP_CONTAINER', 'database-backups')
            
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            container_client = blob_service_client.get_container_client(container_name)
            
            for blob in container_client.list_blobs(name_starts_with='database-backups/'):
                if blob.last_modified.replace(tzinfo=None) < cutoff_date:
                    container_client.delete_blob(blob.name)
                    deleted += 1
                    logger.info(f"Deleted old Azure backup: {blob.name}")
                    
        except Exception as e:
            logger.error(f"Azure cleanup failed: {str(e)}")
            
        return deleted
        
    def restore_backup(self, backup_filename: str, target_database: str = None) -> bool:
        """Restore database from backup"""
        backup_path = self.backup_dir / backup_filename
        
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
            
        try:
            logger.info(f"Starting database restore from: {backup_filename}")
            
            # Determine if backup is encrypted
            if backup_filename.endswith('.enc'):
                if not self.encryption_enabled:
                    raise Exception("Backup is encrypted but encryption key not available")
                    
                # Decrypt backup
                decrypted_path = backup_path.with_suffix('')
                with open(backup_path, 'rb') as f_in:
                    encrypted_data = f_in.read()
                    decrypted_data = self.cipher.decrypt(encrypted_data)
                    
                with open(decrypted_path, 'wb') as f_out:
                    f_out.write(decrypted_data)
                    
                backup_path = decrypted_path
                logger.info("Backup decrypted successfully")
                
            # Decompress if needed
            if backup_filename.endswith('.gz'):
                decompressed_path = backup_path.with_suffix('')
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(decompressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                        
                backup_path = decompressed_path
                logger.info("Backup decompressed successfully")
                
            # Restore database
            target_db = target_database or self.db_config['database']
            
            pg_restore_cmd = [
                'pg_restore',
                '-h', self.db_config['host'],
                '-p', str(self.db_config['port']),
                '-U', self.db_config['username'],
                '-d', target_db,
                '--verbose',
                '--no-password',
                '--clean',
                '--if-exists',
                str(backup_path)
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            result = subprocess.run(
                pg_restore_cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"pg_restore failed: {result.stderr}")
                return False
                
            logger.info("Database restore completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return False
        finally:
            # Clean up temporary files
            for temp_file in [backup_path.with_suffix(''), backup_path.with_suffix('')]:
                if temp_file.exists() and temp_file != self.backup_dir / backup_filename:
                    temp_file.unlink()
                    
    def list_backups(self) -> List[Dict]:
        """List available backups"""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob('actionplan_backup_*')):
            metadata_file = backup_file.with_suffix('.json')
            
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    backups.append(metadata)
                except:
                    # Fallback to file stats
                    stat = backup_file.stat()
                    backups.append({
                        'filename': backup_file.name,
                        'size_bytes': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'success': True
                    })
            else:
                stat = backup_file.stat()
                backups.append({
                    'filename': backup_file.name,
                    'size_bytes': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'success': True
                })
                
        return backups
        
    def verify_backup(self, backup_filename: str) -> bool:
        """Verify backup integrity"""
        backup_path = self.backup_dir / backup_filename
        metadata_path = backup_path.with_suffix('.json')
        
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
            
        try:
            # Check if metadata exists and verify checksum
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    
                expected_checksum = metadata.get('checksum')
                if expected_checksum:
                    actual_checksum = self._calculate_checksum(backup_path)
                    if actual_checksum != expected_checksum:
                        logger.error(f"Checksum mismatch for {backup_filename}")
                        return False
                        
            logger.info(f"Backup verification successful: {backup_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Backup verification failed: {str(e)}")
            return False
            
    def _format_size(self, size_bytes: int) -> str:
        """Format size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
        
    def get_backup_stats(self) -> Dict:
        """Get backup statistics"""
        backups = self.list_backups()
        
        if not backups:
            return {
                'total_backups': 0,
                'total_size': 0,
                'latest_backup': None,
                'success_rate': 0
            }
            
        total_size = sum(b.get('size_bytes', 0) for b in backups)
        successful = sum(1 for b in backups if b.get('success', False))
        latest = max(backups, key=lambda x: x.get('created', ''))
        
        return {
            'total_backups': len(backups),
            'total_size': total_size,
            'total_size_formatted': self._format_size(total_size),
            'latest_backup': latest,
            'success_rate': (successful / len(backups)) * 100 if backups else 0
        }

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Database backup management')
    parser.add_argument('action', choices=['backup', 'restore', 'list', 'cleanup', 'verify', 'stats'],
                       help='Action to perform')
    parser.add_argument('--type', choices=['full', 'incremental'], default='full',
                       help='Backup type (default: full)')
    parser.add_argument('--file', help='Backup filename for restore/verify operations')
    parser.add_argument('--target-db', help='Target database for restore')
    parser.add_argument('--force', action='store_true', help='Force operation without confirmation')
    
    args = parser.parse_args()
    
    try:
        backup_system = DatabaseBackup()
        
        if args.action == 'backup':
            result = backup_system.create_backup(args.type)
            if result['success']:
                print(f"✅ Backup created successfully: {result['filename']}")
                print(f"📊 Size: {backup_system._format_size(result['size_bytes'])}")
                if result.get('compressed_size_bytes'):
                    print(f"📦 Compressed: {backup_system._format_size(result['compressed_size_bytes'])}")
                print(f"⏱️  Duration: {result['duration_seconds']:.2f} seconds")
            else:
                print(f"❌ Backup failed: {result['error']}")
                sys.exit(1)
                
        elif args.action == 'restore':
            if not args.file:
                print("❌ --file argument required for restore")
                sys.exit(1)
                
            if not args.force:
                print(f"⚠️  This will restore database from: {args.file}")
                if args.target_db:
                    print(f"⚠️  Target database: {args.target_db}")
                confirm = input("Continue? (y/N): ")
                if confirm.lower() != 'y':
                    print("Restore cancelled")
                    sys.exit(0)
                    
            success = backup_system.restore_backup(args.file, args.target_db)
            if success:
                print("✅ Restore completed successfully")
            else:
                print("❌ Restore failed")
                sys.exit(1)
                
        elif args.action == 'list':
            backups = backup_system.list_backups()
            if not backups:
                print("No backups found")
            else:
                print(f"📋 Found {len(backups)} backup(s):")
                print("-" * 80)
                for backup in backups:
                    status = "✅" if backup.get('success', True) else "❌"
                    size = backup_system._format_size(backup.get('size_bytes', 0))
                    created = backup.get('created', 'Unknown')
                    print(f"{status} {backup['filename']} ({size}) - {created}")
                    
        elif args.action == 'cleanup':
            if not args.force:
                confirm = input(f"Delete backups older than {backup_system.retention_days} days? (y/N): ")
                if confirm.lower() != 'y':
                    print("Cleanup cancelled")
                    sys.exit(0)
                    
            result = backup_system.cleanup_old_backups()
            print(f"✅ Cleanup completed:")
            print(f"   Local files deleted: {result['deleted_local']}")
            print(f"   Cloud files deleted: {result['deleted_cloud']}")
            if result['errors']:
                print(f"   Errors: {len(result['errors'])}")
                
        elif args.action == 'verify':
            if not args.file:
                print("❌ --file argument required for verify")
                sys.exit(1)
                
            success = backup_system.verify_backup(args.file)
            if success:
                print(f"✅ Backup verification successful: {args.file}")
            else:
                print(f"❌ Backup verification failed: {args.file}")
                sys.exit(1)
                
        elif args.action == 'stats':
            stats = backup_system.get_backup_stats()
            print("📊 Backup Statistics:")
            print(f"   Total backups: {stats['total_backups']}")
            print(f"   Total size: {stats['total_size_formatted']}")
            print(f"   Success rate: {stats['success_rate']:.1f}%")
            if stats['latest_backup']:
                print(f"   Latest backup: {stats['latest_backup']['filename']}")
                
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()warning(f"Generated new encryption key: {key.decode()}")
                logger.warning("Save this key securely - you'll need it to decrypt backups!")
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def _parse_db_url(self, db_url: str) -> Dict[str, str]:
        """Parse database URL into components"""
        import urllib.parse
        
        parsed = urllib.parse.urlparse(db_url)
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:],  # Remove leading slash
            'username': parsed.username,
            'password': parsed.password
        }
        
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['username'],
                password=self.db_config['password']
            )
            conn.close()
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
            
    def get_database_size(self) -> Optional[int]:
        """Get database size in bytes"""
        try:
            conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['username'],
                password=self.db_config['password']
            )
            
            cursor = conn.cursor()
            cursor.execute(f"SELECT pg_database_size('{self.db_config['database']}')")
            size = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return size
        except Exception as e:
            logger.error(f"Failed to get database size: {str(e)}")
            return None
            
    def create_backup(self, backup_type: str = 'full') -> Dict[str, any]:
        """Create database backup"""
        start_time = datetime.utcnow()
        timestamp = start_time.strftime('%Y%m%d_%H%M%S')
        
        # Generate backup filename
        backup_filename = f"actionplan_backup_{backup_type}_{timestamp}.sql"
        backup_path = self.backup_dir / backup_filename
        
        backup_info = {
            'filename': backup_filename,
            'path': str(backup_path),
            'type': backup_type,
            'timestamp': timestamp,
            'start_time': start_time,
            'success': False,
            'size_bytes': 0,
            'compressed_size_bytes': 0,
            'encrypted': False,
            'cloud_uploaded': False,
            'error': None
        }
        
        try:
            logger.info(f"Starting {backup_type} backup: {backup_filename}")
            
            # Test connection first
            if not self.test_connection():
                raise Exception("Database connection test failed")
                
            # Get database size before backup
            db_size = self.get_database_size()
            if db_size:
                logger.info(f"Database size: {self._format_size(db_size)}")
                
            # Create pg_dump command
            pg_dump_cmd = [
                'pg_dump',
                '-h', self.db_config['host'],
                '-p', str(self.db_config['port']),
                '-U', self.db_config['username'],
                '-d', self.db_config['database'],
                '--verbose',
                '--no-password',
                '--format=custom' if backup_type == 'full' else '--format=plain',
                '--file', str(backup_path)
            ]
            
            # Set environment for password
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            # Execute pg_dump
            logger.info("Executing pg_dump...")
            result = subprocess.run(
                pg_dump_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
                
            # Check if backup file was created
            if not backup_path.exists():
                raise Exception("Backup file was not created")
                
            backup_info['size_bytes'] = backup_path.stat().st_size
            logger.info(f"Backup created: {self._format_size(backup_info['size_bytes'])}")
            
            # Compress backup if enabled
            if self.compression == 'gzip':
                compressed_path = backup_path.with_suffix(backup_path.suffix + '.gz')
                logger.info("Compressing backup...")
                
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                        
                # Remove uncompressed file
                backup_path.unlink()
                backup_path = compressed_path
                backup_info['path'] = str(backup_path)
                backup_info['filename'] = backup_path.name
                backup_info['compressed_size_bytes'] = backup_path.stat().st_size
                
                compression_ratio = (1 - backup_info['compressed_size_bytes'] / backup_info['size_bytes']) * 100
                logger.info(f"Compressed to: {self._format_size(backup_info['compressed_size_bytes'])} ({compression_ratio:.1f}% reduction)")
                
            # Encrypt backup if enabled
            if self.encryption_enabled:
                encrypted_path = backup_path.with_suffix(backup_path.suffix + '.enc')
                logger.info("Encrypting backup...")
                
                with open(backup_path, 'rb') as f_in:
                    data = f_in.read()
                    encrypted_data = self.cipher.encrypt(data)
                    
                with open(encrypted_path, 'wb') as f_out:
                    f_out.write(encrypted_data)
                    
                # Remove unencrypted file
                backup_path.unlink()
                backup_path = encrypted_path
                backup_info['path'] = str(backup_path)
                backup_info['filename'] = backup_path.name
                backup_info['encrypted'] = True
                
                logger.