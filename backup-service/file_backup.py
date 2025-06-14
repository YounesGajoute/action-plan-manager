#!/usr/bin/env python3
"""
===================================================================
file_backup.py - File System Backup Handler
===================================================================

Handles file system backups for the Action Plan Manager.
Creates compressed archives of important data directories.

Features:
- Recursive directory archiving
- File exclusion patterns
- Compression (tar.gz)
- Incremental backup support
- Retention management
- Validation and integrity checks

Author: TechMac Development Team
Version: 1.0.0
"""

import os
import logging
import tarfile
import shutil
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Optional, Set

class FileBackup:
    """File system backup handler"""
    
    def __init__(self, data_dir: Path, backup_dir: Path, retention_days: int = 30):
        self.data_dir = Path(data_dir)
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.logger = logging.getLogger(__name__)
        
        # Default exclusion patterns
        self.exclude_patterns = {
            '*.tmp',
            '*.temp',
            '*.log',
            '*.cache',
            '__pycache__',
            '.git',
            '.svn',
            '.DS_Store',
            'Thumbs.db',
            '*.pyc',
            '*.pyo',
            '.pytest_cache'
        }
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Load custom exclusions if they exist
        self._load_exclusions()
        
    def _load_exclusions(self):
        """Load custom exclusion patterns from config file"""
        try:
            exclusions_file = self.backup_dir / 'backup_exclusions.json'
            if exclusions_file.exists():
                with open(exclusions_file, 'r') as f:
                    custom_exclusions = json.load(f)
                    self.exclude_patterns.update(custom_exclusions.get('patterns', []))
                    self.logger.info(f"Loaded {len(custom_exclusions.get('patterns', []))} custom exclusion patterns")
        except Exception as e:
            self.logger.warning(f"Could not load custom exclusions: {e}")
            
    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded from backup"""
        try:
            # Check against exclusion patterns
            for pattern in self.exclude_patterns:
                if file_path.match(pattern) or file_path.name == pattern:
                    return True
                    
            # Check if file is too large (>100MB)
            if file_path.is_file() and file_path.stat().st_size > 100 * 1024 * 1024:
                self.logger.warning(f"Excluding large file: {file_path} ({file_path.stat().st_size / (1024*1024):.1f}MB)")
                return True
                
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking exclusion for {file_path}: {e}")
            return False
            
    def _get_file_list(self, directory: Path) -> List[Path]:
        """Get list of files to backup, excluding unwanted files"""
        files_to_backup = []
        
        try:
            for root, dirs, files in os.walk(directory):
                root_path = Path(root)
                
                # Filter directories (modify in-place to affect os.walk)
                dirs[:] = [d for d in dirs if not self._should_exclude(root_path / d)]
                
                # Add files that should not be excluded
                for file in files:
                    file_path = root_path / file
                    if not self._should_exclude(file_path):
                        files_to_backup.append(file_path)
                        
            self.logger.info(f"Found {len(files_to_backup)} files to backup in {directory}")
            return files_to_backup
            
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")
            return []
            
    def create_backup(self, backup_type: str = 'full') -> Dict[str, any]:
        """
        Create a file backup
        
        Args:
            backup_type: 'full' (default) or 'incremental'
            
        Returns:
            Dict with success status, file path, and details
        """
        try:
            if not self.data_dir.exists():
                return {
                    'success': False,
                    'error': f'Data directory does not exist: {self.data_dir}',
                    'file_path': None
                }
                
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"actionplan_files_{backup_type}_{timestamp}.tar.gz"
            backup_path = self.backup_dir / filename
            
            self.logger.info(f"Starting {backup_type} file backup: {filename}")
            
            # Get files to backup
            if backup_type == 'incremental':
                files_to_backup = self._get_incremental_files()
            else:
                files_to_backup = self._get_file_list(self.data_dir)
                
            if not files_to_backup:
                return {
                    'success': False,
                    'error': 'No files to backup',
                    'file_path': None
                }
                
            # Create tar.gz archive
            result = self._create_archive(backup_path, files_to_backup)
            
            if result['success']:
                # Create backup manifest
                manifest = self._create_manifest(backup_path, files_to_backup, backup_type)
                
                # Validate backup
                if self._validate_backup(backup_path):
                    self.logger.info(f"File backup created successfully: {backup_path}")
                    return {
                        'success': True,
                        'file_path': str(backup_path),
                        'backup_type': backup_type,
                        'file_count': len(files_to_backup),
                        'size': backup_path.stat().st_size,
                        'manifest': manifest
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Backup validation failed',
                        'file_path': str(backup_path)
                    }
            else:
                return result
                
        except Exception as e:
            self.logger.error(f"File backup failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': None
            }
            
    def _get_incremental_files(self) -> List[Path]:
        """Get files for incremental backup (modified since last backup)"""
        try:
            # Find the most recent successful backup
            last_backup = self._get_last_backup_time()
            
            if not last_backup:
                self.logger.info("No previous backup found, performing full backup")
                return self._get_file_list(self.data_dir)
                
            self.logger.info(f"Finding files modified since {last_backup}")
            
            incremental_files = []
            all_files = self._get_file_list(self.data_dir)
            
            for file_path in all_files:
                try:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime > last_backup:
                        incremental_files.append(file_path)
                except Exception as e:
                    self.logger.warning(f"Could not check modification time for {file_path}: {e}")
                    
            self.logger.info(f"Found {len(incremental_files)} files for incremental backup")
            return incremental_files
            
        except Exception as e:
            self.logger.error(f"Error determining incremental files: {e}")
            return self._get_file_list(self.data_dir)
            
    def _get_last_backup_time(self) -> Optional[datetime]:
        """Get timestamp of last successful backup"""
        try:
            manifests = list(self.backup_dir.glob('*_manifest.json'))
            if not manifests:
                return None
                
            # Sort by modification time and get the most recent
            manifests.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            with open(manifests[0], 'r') as f:
                manifest = json.load(f)
                return datetime.fromisoformat(manifest['timestamp'])
                
        except Exception as e:
            self.logger.warning(f"Could not determine last backup time: {e}")
            return None
            
    def _create_archive(self, backup_path: Path, files_to_backup: List[Path]) -> Dict[str, any]:
        """Create compressed tar archive"""
        try:
            with tarfile.open(backup_path, 'w:gz', compresslevel=6) as tar:
                for file_path in files_to_backup:
                    try:
                        # Calculate relative path from data directory
                        relative_path = file_path.relative_to(self.data_dir)
                        tar.add(file_path, arcname=relative_path)
                    except Exception as e:
                        self.logger.warning(f"Could not add {file_path} to archive: {e}")
                        
            return {
                'success': True,
                'archive_path': str(backup_path),
                'compressed_size': backup_path.stat().st_size
            }
            
        except Exception as e:
            self.logger.error(f"Archive creation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def _create_manifest(self, backup_path: Path, files_backed_up: List[Path], backup_type: str) -> Dict[str, any]:
        """Create backup manifest with metadata"""
        try:
            manifest = {
                'backup_file': backup_path.name,
                'timestamp': datetime.now().isoformat(),
                'backup_type': backup_type,
                'file_count': len(files_backed_up),
                'total_size': sum(f.stat().st_size for f in files_backed_up if f.exists()),
                'compressed_size': backup_path.stat().st_size,
                'data_directory': str(self.data_dir),
                'files': []
            }
            
            # Add file details
            for file_path in files_backed_up:
                try:
                    stat = file_path.stat()
                    relative_path = file_path.relative_to(self.data_dir)
                    
                    manifest['files'].append({
                        'path': str(relative_path),
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'checksum': self._calculate_checksum(file_path)
                    })
                except Exception as e:
                    self.logger.warning(f"Could not add {file_path} to manifest: {e}")
                    
            # Save manifest
            manifest_path = backup_path.with_suffix('.manifest.json')
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
                
            self.logger.info(f"Backup manifest created: {manifest_path}")
            return manifest
            
        except Exception as e:
            self.logger.error(f"Manifest creation failed: {e}")
            return {}
            
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum for file"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.warning(f"Could not calculate checksum for {file_path}: {e}")
            return ""
            
    def _validate_backup(self, backup_path: Path) -> bool:
        """Validate backup archive integrity"""
        try:
            # Test if tar file can be opened and read
            with tarfile.open(backup_path, 'r:gz') as tar:
                # Try to get list of members
                members = tar.getmembers()
                
                # Verify we have some content
                if not members:
                    self.logger.error("Backup archive is empty")
                    return False
                    
                # Test extraction of a few files
                test_count = min(5, len(members))
                for i, member in enumerate(members[:test_count]):
                    try:
                        tar.extractfile(member)
                    except Exception as e:
                        self.logger.error(f"Could not extract test file {member.name}: {e}")
                        return False
                        
            self.logger.info(f"Backup validation successful: {len(members)} files in archive")
            return True
            
        except Exception as e:
            self.logger.error(f"Backup validation failed: {e}")
            return False
            
    def list_backups(self) -> List[Dict[str, any]]:
        """List all available file backups"""
        try:
            backups = []
            
            # Find all backup files
            for backup_file in self.backup_dir.glob('actionplan_files_*.tar.gz'):
                try:
                    stat = backup_file.stat()
                    
                    # Try to load manifest
                    manifest_path = backup_file.with_suffix('.manifest.json')
                    manifest = {}
                    if manifest_path.exists():
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                            
                    # Determine backup type from filename
                    backup_type = 'full'
                    if '_incremental_' in backup_file.name:
                        backup_type = 'incremental'
                        
                    backups.append({
                        'filename': backup_file.name,
                        'path': str(backup_file),
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime),
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                        'backup_type': backup_type,
                        'file_count': manifest.get('file_count', 0),
                        'total_size': manifest.get('total_size', 0),
                        'has_manifest': manifest_path.exists()
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Could not process backup file {backup_file}: {e}")
                    
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
            
            self.logger.info(f"Cleaning up file backups older than {self.retention_days} days")
            
            # Find all backup files and manifests
            for backup_file in self.backup_dir.glob('actionplan_files_*.tar.gz'):
                try:
                    file_date = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    
                    if file_date < cutoff_date:
                        # Remove backup file
                        backup_file.unlink()
                        removed_count += 1
                        self.logger.info(f"Removed old backup: {backup_file.name}")
                        
                        # Remove associated manifest
                        manifest_path = backup_file.with_suffix('.manifest.json')
                        if manifest_path.exists():
                            manifest_path.unlink()
                            self.logger.info(f"Removed manifest: {manifest_path.name}")
                            
                except Exception as e:
                    self.logger.error(f"Failed to remove {backup_file.name}: {e}")
                    
            if removed_count > 0:
                self.logger.info(f"Cleanup completed: {removed_count} old file backups removed")
            else:
                self.logger.info("No old file backups to remove")
                
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return 0
            
    def restore_backup(self, backup_path: str, restore_dir: Path = None) -> Dict[str, any]:
        """
        Restore files from backup
        
        Args:
            backup_path: Path to backup archive
            restore_dir: Directory to restore to (defaults to original data directory)
            
        Returns:
            Dict with success status and details
        """
        try:
            backup_file = Path(backup_path)
            target_dir = restore_dir or self.data_dir
            
            if not backup_file.exists():
                return {
                    'success': False,
                    'error': 'Backup file does not exist'
                }
                
            self.logger.info(f"Restoring files from {backup_path} to {target_dir}")
            
            # Create target directory if it doesn't exist
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract archive
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(path=target_dir)
                extracted_files = tar.getnames()
                
            self.logger.info(f"Successfully restored {len(extracted_files)} files")
            
            return {
                'success': True,
                'restored_files': len(extracted_files),
                'restore_directory': str(target_dir)
            }
            
        except Exception as e:
            self.logger.error(f"File restore failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def verify_backup(self, backup_path: str) -> Dict[str, any]:
        """Verify backup integrity against manifest"""
        try:
            backup_file = Path(backup_path)
            manifest_path = backup_file.with_suffix('.manifest.json')
            
            if not manifest_path.exists():
                return {
                    'success': False,
                    'error': 'No manifest file found for verification'
                }
                
            # Load manifest
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                
            # Verify archive can be read
            with tarfile.open(backup_path, 'r:gz') as tar:
                archive_members = {m.name: m for m in tar.getmembers()}
                
            # Check if all manifest files are in archive
            missing_files = []
            for file_info in manifest['files']:
                if file_info['path'] not in archive_members:
                    missing_files.append(file_info['path'])
                    
            if missing_files:
                return {
                    'success': False,
                    'error': f'Missing files in archive: {missing_files[:5]}...' if len(missing_files) > 5 else f'Missing files: {missing_files}'
                }
                
            return {
                'success': True,
                'verified_files': len(manifest['files']),
                'backup_type': manifest['backup_type'],
                'timestamp': manifest['timestamp']
            }
            
        except Exception as e:
            self.logger.error(f"Backup verification failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

def main():
    """CLI interface for file backup operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description='File Backup Utility')
    parser.add_argument('--data-dir', required=True, help='Data directory to backup')
    parser.add_argument('--backup-dir', required=True, help='Backup directory path')
    parser.add_argument('--action', choices=['backup', 'list', 'cleanup', 'restore', 'verify'], 
                       default='backup', help='Action to perform')
    parser.add_argument('--backup-type', choices=['full', 'incremental'], default='full',
                       help='Backup type')
    parser.add_argument('--retention-days', type=int, default=30,
                       help='Backup retention period in days')
    parser.add_argument('--restore-file', help='Backup file to restore from')
    parser.add_argument('--restore-dir', help='Directory to restore files to')
    parser.add_argument('--verify-file', help='Backup file to verify')
    
    args = parser.parse_args()
    
    # Setup logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Initialize backup handler
    backup_handler = FileBackup(
        data_dir=Path(args.data_dir),
        backup_dir=Path(args.backup_dir),
        retention_days=args.retention_days
    )
    
    if args.action == 'backup':
        print(f"Creating {args.backup_type} file backup...")
        result = backup_handler.create_backup(args.backup_type)
        if result['success']:
            print(f"Backup created successfully: {result['file_path']}")
            print(f"Files backed up: {result['file_count']}")
            size_mb = result['size'] / (1024 * 1024)
            print(f"Archive size: {size_mb:.1f}MB")
        else:
            print(f"Backup failed: {result['error']}")
            
    elif args.action == 'list':
        print("Available file backups:")
        backups = backup_handler.list_backups()
        for backup in backups:
            size_mb = backup['size'] / (1024 * 1024)
            print(f"  {backup['filename']} - {backup['backup_type']} - {size_mb:.1f}MB - {backup['created']}")
            
    elif args.action == 'cleanup':
        print(f"Cleaning up backups older than {args.retention_days} days...")
        removed = backup_handler.cleanup_old_backups()
        print(f"Removed {removed} old backup files")
        
    elif args.action == 'restore':
        if not args.restore_file:
            print("Error: --restore-file is required for restore action")
            return
            
        restore_dir = Path(args.restore_dir) if args.restore_dir else None
        print(f"Restoring files from {args.restore_file}...")
        result = backup_handler.restore_backup(args.restore_file, restore_dir)
        if result['success']:
            print(f"Successfully restored {result['restored_files']} files")
        else:
            print(f"Restore failed: {result['error']}")
            
    elif args.action == 'verify':
        if not args.verify_file:
            print("Error: --verify-file is required for verify action")
            return
            
        print(f"Verifying backup {args.verify_file}...")
        result = backup_handler.verify_backup(args.verify_file)
        if result['success']:
            print(f"Backup verification successful - {result['verified_files']} files verified")
        else:
            print(f"Verification failed: {result['error']}")

if __name__ == "__main__":
    main()