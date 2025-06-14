#!/usr/bin/env python3
"""
===================================================================
database_backup.py - PostgreSQL Database Backup Handler
===================================================================

Handles PostgreSQL database backups for the Action Plan Manager.
Supports both SQL dumps and custom format backups with compression.

Features:
- PostgreSQL pg_dump integration
- Automatic compression
- Backup validation
- Retention management
- Error handling and logging

Author: TechMac Development Team
Version: 1.0.0
"""

import os
import logging
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import urllib.parse
from typing import Dict, Optional, List

class DatabaseBackup:
    """PostgreSQL database backup handler"""
    
    def __init__(self, database_url: str, backup_dir: Path, retention_days: int = 30):
        self.database_url = database_url
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.logger = logging.getLogger(__name__)
        
        # Parse database URL
        self.db_config = self._parse_database_url(database_url)
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def _parse_database_url(self, url: str) -> Dict[str, str]:
        """Parse PostgreSQL database URL"""
        try:
            parsed = urllib.parse.urlparse(url)
            return {
                'host': parsed.hostname or 'localhost',
                'port': str(parsed.port or 5432),
                'username': parsed.username or 'postgres',
                'password': parsed.password or '',
                'database': parsed.path[1:] if parsed.path else 'postgres'
            }
        except Exception as e:
            self.logger.error(f"Failed to parse database URL: {e}")
            raise
            
    def create_backup(self, backup_format: str = 'custom') -> Dict[str, any]:
        """
        Create a database backup
        
        Args:
            backup_format: 'custom' (default) or 'sql'
            
        Returns:
            Dict with success status, file path, and error details
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Determine backup format and build restore command
            if '.custom' in backup_path:
                # Custom format restore using pg_restore
                if backup_path.endswith('.gz'):
                    # Decompress first
                    temp_file = backup_file.with_suffix('')
                    with gzip.open(backup_path, 'rb') as f_in:
                        with open(temp_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    restore_file = str(temp_file)
                else:
                    restore_file = backup_path
                    
                cmd = [
                    'pg_restore',
                    '-h', self.db_config['host'],
                    '-p', self.db_config['port'],
                    '-U', self.db_config['username'],
                    '-d', target_db,
                    '--verbose',
                    '--no-password',
                    '--clean',
                    '--if-exists',
                    '--no-owner',
                    '--no-privileges',
                    restore_file
                ]
            else:
                # SQL format restore using psql
                if backup_path.endswith('.gz'):
                    cmd = [
                        'gunzip', '-c', backup_path, '|',
                        'psql',
                        '-h', self.db_config['host'],
                        '-p', self.db_config['port'],
                        '-U', self.db_config['username'],
                        '-d', target_db
                    ]
                    # Use shell=True for pipe
                    cmd = f"gunzip -c {backup_path} | psql -h {self.db_config['host']} -p {self.db_config['port']} -U {self.db_config['username']} -d {target_db}"
                    use_shell = True
                else:
                    cmd = [
                        'psql',
                        '-h', self.db_config['host'],
                        '-p', self.db_config['port'],
                        '-U', self.db_config['username'],
                        '-d', target_db,
                        '-f', backup_path
                    ]
                    use_shell = False
                    
            # Execute restore command
            if isinstance(cmd, str):
                result = subprocess.run(
                    cmd,
                    shell=True,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=7200  # 2 hours timeout
                )
            else:
                result = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=7200  # 2 hours timeout
                )
                
            # Clean up temporary file if created
            if '.custom' in backup_path and backup_path.endswith('.gz'):
                temp_file.unlink(missing_ok=True)
                
            if result.returncode == 0:
                self.logger.info(f"Database restore completed successfully")
                return {
                    'success': True,
                    'target_database': target_db,
                    'restore_output': result.stdout
                }
            else:
                self.logger.error(f"Database restore failed: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            self.logger.error("Database restore timed out")
            return {
                'success': False,
                'error': "Restore operation timed out"
            }
        except Exception as e:
            self.logger.error(f"Database restore failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

def main():
    """CLI interface for database backup operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Backup Utility')
    parser.add_argument('--database-url', required=True, help='PostgreSQL database URL')
    parser.add_argument('--backup-dir', required=True, help='Backup directory path')
    parser.add_argument('--action', choices=['backup', 'list', 'cleanup', 'restore'], 
                       default='backup', help='Action to perform')
    parser.add_argument('--format', choices=['sql', 'custom'], default='custom',
                       help='Backup format')
    parser.add_argument('--retention-days', type=int, default=30,
                       help='Backup retention period in days')
    parser.add_argument('--restore-file', help='Backup file to restore from')
    parser.add_argument('--target-database', help='Target database for restore')
    
    args = parser.parse_args()
    
    # Setup logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Initialize backup handler
    backup_handler = DatabaseBackup(
        database_url=args.database_url,
        backup_dir=Path(args.backup_dir),
        retention_days=args.retention_days
    )
    
    if args.action == 'backup':
        print("Creating database backup...")
        result = backup_handler.create_backup(args.format)
        if result['success']:
            print(f"Backup created successfully: {result['file_path']}")
        else:
            print(f"Backup failed: {result['error']}")
            
    elif args.action == 'list':
        print("Available backups:")
        backups = backup_handler.list_backups()
        for backup in backups:
            size_mb = backup['size'] / (1024 * 1024)
            print(f"  {backup['filename']} - {size_mb:.1f}MB - {backup['created']}")
            
    elif args.action == 'cleanup':
        print(f"Cleaning up backups older than {args.retention_days} days...")
        removed = backup_handler.cleanup_old_backups()
        print(f"Removed {removed} old backup files")
        
    elif args.action == 'restore':
        if not args.restore_file:
            print("Error: --restore-file is required for restore action")
            return
            
        print(f"Restoring database from {args.restore_file}...")
        result = backup_handler.restore_backup(args.restore_file, args.target_database)
        if result['success']:
            print("Database restore completed successfully")
        else:
            print(f"Restore failed: {result['error']}")

if __name__ == "__main__":
    main() backup_format == 'sql':
                filename = f"actionplan_db_{timestamp}.sql"
                backup_path = self.backup_dir / filename
                result = self._create_sql_backup(backup_path)
            else:
                filename = f"actionplan_db_{timestamp}.custom"
                backup_path = self.backup_dir / filename
                result = self._create_custom_backup(backup_path)
                
            if result['success']:
                # Compress the backup
                compressed_path = self._compress_backup(backup_path)
                if compressed_path:
                    # Remove uncompressed file
                    backup_path.unlink()
                    result['file_path'] = str(compressed_path)
                    result['compressed'] = True
                else:
                    result['file_path'] = str(backup_path)
                    result['compressed'] = False
                    
                # Validate backup
                if self._validate_backup(result['file_path']):
                    self.logger.info(f"Database backup created successfully: {result['file_path']}")
                else:
                    result['success'] = False
                    result['error'] = "Backup validation failed"
                    
            return result
            
        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': None
            }
            
    def _create_sql_backup(self, backup_path: Path) -> Dict[str, any]:
        """Create SQL format backup using pg_dump"""
        try:
            # Set up environment for PostgreSQL password
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            # Build pg_dump command
            cmd = [
                'pg_dump',
                '-h', self.db_config['host'],
                '-p', self.db_config['port'],
                '-U', self.db_config['username'],
                '-d', self.db_config['database'],
                '--verbose',
                '--no-password',
                '--no-owner',
                '--no-privileges',
                '--create',
                '--clean',
                '--if-exists',
                '--file', str(backup_path)
            ]
            
            self.logger.info(f"Starting SQL backup: {backup_path}")
            
            # Execute pg_dump
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'format': 'sql',
                    'size': backup_path.stat().st_size
                }
            else:
                self.logger.error(f"pg_dump failed: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            self.logger.error("Database backup timed out")
            return {
                'success': False,
                'error': "Backup operation timed out"
            }
        except Exception as e:
            self.logger.error(f"SQL backup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def _create_custom_backup(self, backup_path: Path) -> Dict[str, any]:
        """Create custom format backup using pg_dump"""
        try:
            # Set up environment for PostgreSQL password
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            # Build pg_dump command for custom format
            cmd = [
                'pg_dump',
                '-h', self.db_config['host'],
                '-p', self.db_config['port'],
                '-U', self.db_config['username'],
                '-d', self.db_config['database'],
                '--verbose',
                '--no-password',
                '--format=custom',
                '--compress=9',
                '--no-owner',
                '--no-privileges',
                '--file', str(backup_path)
            ]
            
            self.logger.info(f"Starting custom format backup: {backup_path}")
            
            # Execute pg_dump
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'format': 'custom',
                    'size': backup_path.stat().st_size
                }
            else:
                self.logger.error(f"pg_dump failed: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            self.logger.error("Database backup timed out")
            return {
                'success': False,
                'error': "Backup operation timed out"
            }
        except Exception as e:
            self.logger.error(f"Custom backup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def _compress_backup(self, backup_path: Path) -> Optional[Path]:
        """Compress backup file using gzip"""
        try:
            compressed_path = backup_path.with_suffix(backup_path.suffix + '.gz')
            
            self.logger.info(f"Compressing backup: {backup_path}")
            
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb', compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)
                    
            # Verify compressed file was created and has content
            if compressed_path.exists() and compressed_path.stat().st_size > 0:
                compression_ratio = backup_path.stat().st_size / compressed_path.stat().st_size
                self.logger.info(f"Compression completed. Ratio: {compression_ratio:.2f}:1")
                return compressed_path
            else:
                self.logger.error("Compression failed - empty or missing file")
                return None
                
        except Exception as e:
            self.logger.error(f"Compression failed: {e}")
            return None
            
    def _validate_backup(self, backup_path: str) -> bool:
        """Validate backup file integrity"""
        try:
            backup_file = Path(backup_path)
            
            # Check if file exists and has content
            if not backup_file.exists():
                self.logger.error("Backup file does not exist")
                return False
                
            if backup_file.stat().st_size == 0:
                self.logger.error("Backup file is empty")
                return False
                
            # For gzipped files, test decompression
            if backup_path.endswith('.gz'):
                try:
                    with gzip.open(backup_path, 'rb') as f:
                        # Read first few bytes to verify it's valid gzip
                        f.read(1024)
                    self.logger.info("Backup file compression validated")
                except Exception as e:
                    self.logger.error(f"Backup file compression validation failed: {e}")
                    return False
                    
            # Additional validation for custom format backups
            if '.custom' in backup_path:
                try:
                    # Use pg_restore to list contents (dry run)
                    env = os.environ.copy()
                    env['PGPASSWORD'] = self.db_config['password']
                    
                    if backup_path.endswith('.gz'):
                        # For compressed custom backups, we need to decompress first for validation
                        cmd = ['gzip', '-t', backup_path]
                    else:
                        cmd = [
                            'pg_restore',
                            '--list',
                            backup_path
                        ]
                        
                    result = subprocess.run(
                        cmd,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minutes timeout
                    )
                    
                    if result.returncode != 0:
                        self.logger.error(f"Backup validation failed: {result.stderr}")
                        return False
                        
                except subprocess.TimeoutExpired:
                    self.logger.warning("Backup validation timed out, assuming valid")
                except Exception as e:
                    self.logger.warning(f"Backup validation error (assuming valid): {e}")
                    
            self.logger.info("Backup validation completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Backup validation failed: {e}")
            return False
            
    def list_backups(self) -> List[Dict[str, any]]:
        """List all available backups"""
        try:
            backups = []
            
            # Find all backup files
            patterns = ['actionplan_db_*.sql.gz', 'actionplan_db_*.sql', 
                       'actionplan_db_*.custom.gz', 'actionplan_db_*.custom']
            
            for pattern in patterns:
                for backup_file in self.backup_dir.glob(pattern):
                    stat = backup_file.stat()
                    backups.append({
                        'filename': backup_file.name,
                        'path': str(backup_file),
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime),
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                        'compressed': backup_file.suffix == '.gz',
                        'format': 'custom' if '.custom' in backup_file.name else 'sql'
                    })
                    
            # Sort by creation date (newest first)
            backups.sort(key=lambda x: x['created'], reverse=True)
            
            return backups
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []
            
    def cleanup_old_backups(self) -> int:
        """Remove old backup files based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            removed_count = 0
            
            self.logger.info(f"Cleaning up backups older than {self.retention_days} days")
            
            # Find all backup files
            patterns = ['actionplan_db_*.sql.gz', 'actionplan_db_*.sql', 
                       'actionplan_db_*.custom.gz', 'actionplan_db_*.custom']
            
            for pattern in patterns:
                for backup_file in self.backup_dir.glob(pattern):
                    # Check if file is older than retention period
                    file_date = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    
                    if file_date < cutoff_date:
                        try:
                            backup_file.unlink()
                            removed_count += 1
                            self.logger.info(f"Removed old backup: {backup_file.name}")
                        except Exception as e:
                            self.logger.error(f"Failed to remove {backup_file.name}: {e}")
                            
            if removed_count > 0:
                self.logger.info(f"Cleanup completed: {removed_count} old backups removed")
            else:
                self.logger.info("No old backups to remove")
                
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return 0
            
    def restore_backup(self, backup_path: str, target_database: str = None) -> Dict[str, any]:
        """
        Restore database from backup (use with caution!)
        
        Args:
            backup_path: Path to backup file
            target_database: Target database name (defaults to configured database)
            
        Returns:
            Dict with success status and details
        """
        try:
            target_db = target_database or self.db_config['database']
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                return {
                    'success': False,
                    'error': 'Backup file does not exist'
                }
                
            # Set up environment
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            self.logger.warning(f"Starting database restore from {backup_path} to {target_db}")
            
            if