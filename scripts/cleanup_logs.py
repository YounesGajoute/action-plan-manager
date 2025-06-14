import os
import sys
import logging
import argparse
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LogCleaner:
    """Log cleanup and rotation management"""
    
    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)
        self.stats = {
            'files_processed': 0,
            'files_deleted': 0,
            'bytes_saved': 0,
            'errors': []
        }
        
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'log_directories': [
                'logs/api',
                'logs/nginx', 
                'logs/sync',
                'logs/telegram',
                'logs/email',
                'logs/backup'
            ],
            'retention_days': 30,
            'compress_after_days': 7,
            'max_file_size_mb': 100,
            'file_patterns': ['*.log', '*.out', '*.err'],
            'exclude_patterns': ['*.gz', '*.zip'],
            'compress_format': 'gzip'
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
                
        return default_config
        
    def cleanup_logs(self, dry_run: bool = False) -> Dict:
        """Main cleanup function"""
        logger.info(f"Starting log cleanup (dry_run: {dry_run})")
        
        for log_dir in self.config['log_directories']:
            if os.path.exists(log_dir):
                self._process_directory(log_dir, dry_run)
            else:
                logger.warning(f"Log directory not found: {log_dir}")
                
        logger.info(f"Cleanup completed: {self.stats}")
        return self.stats
        
    def _process_directory(self, directory: str, dry_run: bool):
        """Process a single log directory"""
        logger.info(f"Processing directory: {directory}")
        
        path = Path(directory)
        cutoff_date = datetime.now() - timedelta(days=self.config['retention_days'])
        compress_date = datetime.now() - timedelta(days=self.config['compress_after_days'])
        
        for pattern in self.config['file_patterns']:
            for file_path in path.glob(pattern):
                try:
                    self._process_file(file_path, cutoff_date, compress_date, dry_run)
                    self.stats['files_processed'] += 1
                except Exception as e:
                    error_msg = f"Error processing {file_path}: {str(e)}"
                    logger.error(error_msg)
                    self.stats['errors'].append(error_msg)
                    
    def _process_file(self, file_path: Path, cutoff_date: datetime, compress_date: datetime, dry_run: bool):
        """Process a single log file"""
        file_stat = file_path.stat()
        file_modified = datetime.fromtimestamp(file_stat.st_mtime)
        file_size_mb = file_stat.st_size / (1024 * 1024)
        
        # Skip if file matches exclude patterns
        for exclude_pattern in self.config['exclude_patterns']:
            if file_path.match(exclude_pattern):
                return
                
        # Delete old files
        if file_modified < cutoff_date:
            logger.info(f"Deleting old file: {file_path}")
            if not dry_run:
                file_path.unlink()
            self.stats['files_deleted'] += 1
            self.stats['bytes_saved'] += file_stat.st_size
            return
            
        # Compress files older than compress_date or larger than max_size
        should_compress = (
            file_modified < compress_date or 
            file_size_mb > self.config['max_file_size_mb']
        )
        
        if should_compress and not str(file_path).endswith('.gz'):
            self._compress_file(file_path, dry_run)
            
    def _compress_file(self, file_path: Path, dry_run: bool):
        """Compress a log file"""
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        
        logger.info(f"Compressing: {file_path} -> {compressed_path}")
        
        if not dry_run:
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                    
            # Preserve timestamps
            shutil.copystat(file_path, compressed_path)
            
            # Calculate space saved
            original_size = file_path.stat().st_size
            compressed_size = compressed_path.stat().st_size
            space_saved = original_size - compressed_size
            
            # Remove original file
            file_path.unlink()
            
            self.stats['bytes_saved'] += space_saved
            
        self.stats['files_compressed'] += 1
        
    def get_log_statistics(self) -> Dict:
        """Get detailed log statistics"""
        stats = {
            'directories': {},
            'total_size': 0,
            'total_files': 0,
            'compressed_files': 0,
            'oldest_file': None,
            'largest_file': None
        }
        
        for log_dir in self.config['log_directories']:
            if not os.path.exists(log_dir):
                continue
                
            dir_stats = {
                'files': 0,
                'size': 0,
                'compressed': 0,
                'oldest': None,
                'largest': None
            }
            
            path = Path(log_dir)
            
            for pattern in self.config['file_patterns']:
                for file_path in path.glob(pattern):
                    try:
                        file_stat = file_path.stat()
                        file_modified = datetime.fromtimestamp(file_stat.st_mtime)
                        
                        dir_stats['files'] += 1
                        dir_stats['size'] += file_stat.st_size
                        
                        if str(file_path).endswith('.gz'):
                            dir_stats['compressed'] += 1
                            
                        if not dir_stats['oldest'] or file_modified < dir_stats['oldest'][1]:
                            dir_stats['oldest'] = (str(file_path), file_modified)
                            
                        if not dir_stats['largest'] or file_stat.st_size > dir_stats['largest'][1]:
                            dir_stats['largest'] = (str(file_path), file_stat.st_size)
                            
                    except Exception as e:
                        logger.warning(f"Error getting stats for {file_path}: {e}")
                        
            stats['directories'][log_dir] = dir_stats
            stats['total_files'] += dir_stats['files']
            stats['total_size'] += dir_stats['size']
            stats['compressed_files'] += dir_stats['compressed']
            
            # Update global oldest and largest
            if dir_stats['oldest'] and (not stats['oldest_file'] or 
                                      dir_stats['oldest'][1] < stats['oldest_file'][1]):
                stats['oldest_file'] = dir_stats['oldest']
                
            if dir_stats['largest'] and (not stats['largest_file'] or 
                                       dir_stats['largest'][1] > stats['largest_file'][1]):
                stats['largest_file'] = dir_stats['largest']
                
        return stats