#!/usr/bin/env python3
"""
===================================================================
backup_service.py - Main Backup Service Controller
===================================================================

Main orchestrator for the backup service that coordinates database,
file, and cloud storage backups for the Action Plan Manager.

Features:
- Scheduled backup execution
- Health monitoring
- Status reporting
- Error handling and notifications
- Integration with Redis for status tracking

Author: TechMac Development Team
Version: 1.0.0
"""

import os
import sys
import logging
import time
import schedule
import threading
import signal
from datetime import datetime
from pathlib import Path
import json
import redis
from typing import Dict, Any

# Import backup modules
from database_backup import DatabaseBackup
from file_backup import FileBackup
from s3_uploader import S3Uploader

class BackupService:
    """Main backup service orchestrator"""
    
    def __init__(self):
        self.setup_logging()
        self.load_config()
        self.setup_services()
        self.setup_redis()
        self.running = False
        
    def setup_logging(self):
        """Configure logging"""
        log_dir = Path("/app/logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/app/logs/backup_service.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_config(self):
        """Load configuration from environment variables"""
        self.config = {
            # Backup schedule (cron format)
            'backup_schedule': os.getenv('BACKUP_SCHEDULE', '0 2 * * *'),  # 2 AM daily
            'backup_retention_days': int(os.getenv('BACKUP_RETENTION_DAYS', '30')),
            
            # Paths
            'backup_dir': Path('/app/backups'),
            'data_dir': Path('/app/data'),
            
            # Database
            'database_url': os.getenv('DATABASE_URL', 'postgresql://actionplan:password@db:5432/actionplan'),
            
            # S3 Configuration
            's3_bucket': os.getenv('BACKUP_S3_BUCKET'),
            'aws_access_key': os.getenv('AWS_ACCESS_KEY_ID'),
            'aws_secret_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'aws_region': os.getenv('AWS_REGION', 'us-east-1'),
            
            # Redis
            'redis_url': os.getenv('REDIS_URL', 'redis://cache:6379'),
            
            # Email notifications
            'smtp_server': os.getenv('SMTP_SERVER'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'smtp_user': os.getenv('SMTP_USER'),
            'smtp_password': os.getenv('SMTP_PASSWORD'),
            'notification_email': os.getenv('BACKUP_NOTIFICATION_EMAIL'),
        }
        
        # Create directories
        self.config['backup_dir'].mkdir(exist_ok=True)
        
        self.logger.info("Configuration loaded successfully")
        
    def setup_services(self):
        """Initialize backup services"""
        try:
            # Database backup service
            self.db_backup = DatabaseBackup(
                database_url=self.config['database_url'],
                backup_dir=self.config['backup_dir'],
                retention_days=self.config['backup_retention_days']
            )
            
            # File backup service
            self.file_backup = FileBackup(
                data_dir=self.config['data_dir'],
                backup_dir=self.config['backup_dir'],
                retention_days=self.config['backup_retention_days']
            )
            
            # S3 uploader (if configured)
            if self.config['s3_bucket'] and self.config['aws_access_key']:
                self.s3_uploader = S3Uploader(
                    bucket=self.config['s3_bucket'],
                    access_key=self.config['aws_access_key'],
                    secret_key=self.config['aws_secret_key'],
                    region=self.config['aws_region']
                )
                self.logger.info("S3 uploader initialized")
            else:
                self.s3_uploader = None
                self.logger.info("S3 backup disabled - no credentials provided")
                
            self.logger.info("Backup services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize backup services: {e}")
            raise
            
    def setup_redis(self):
        """Setup Redis connection for status tracking"""
        try:
            self.redis_client = redis.from_url(self.config['redis_url'])
            self.redis_client.ping()
            self.logger.info("Redis connection established")
        except Exception as e:
            self.logger.error(f"Redis connection failed: {e}")
            self.redis_client = None
            
    def update_status(self, operation: str, status: str, details: str = ""):
        """Update operation status in Redis"""
        if not self.redis_client:
            return
            
        try:
            status_data = {
                'timestamp': datetime.now().isoformat(),
                'status': status,
                'details': details
            }
            
            self.redis_client.setex(
                f"backup:status:{operation}",
                86400,  # 24 hours TTL
                json.dumps(status_data)
            )
            
            if status == 'success':
                self.redis_client.setex(
                    f"backup:last_success:{operation}",
                    86400 * 7,  # 7 days TTL
                    datetime.now().isoformat()
                )
                
        except Exception as e:
            self.logger.error(f"Failed to update status: {e}")
            
    def run_backup_cycle(self):
        """Execute complete backup cycle"""
        self.logger.info("=== Starting backup cycle ===")
        
        backup_results = {}
        
        try:
            # Update overall status
            self.update_status('backup_cycle', 'running', 'Backup cycle started')
            
            # Database backup
            self.logger.info("Starting database backup...")
            db_result = self.db_backup.create_backup()
            backup_results['database'] = db_result
            
            if db_result['success']:
                self.logger.info(f"Database backup completed: {db_result['file_path']}")
                self.update_status('database', 'success', db_result['file_path'])
                
                # Upload to S3 if configured
                if self.s3_uploader and db_result['file_path']:
                    s3_result = self.s3_uploader.upload_file(
                        db_result['file_path'],
                        f"database/{Path(db_result['file_path']).name}"
                    )
                    backup_results['database_s3'] = s3_result
                    
                    if s3_result['success']:
                        self.logger.info("Database backup uploaded to S3")
                    else:
                        self.logger.error(f"S3 upload failed: {s3_result['error']}")
            else:
                self.logger.error(f"Database backup failed: {db_result['error']}")
                self.update_status('database', 'failed', db_result['error'])
                
            # File backup
            self.logger.info("Starting file backup...")
            file_result = self.file_backup.create_backup()
            backup_results['files'] = file_result
            
            if file_result['success']:
                self.logger.info(f"File backup completed: {file_result['file_path']}")
                self.update_status('files', 'success', file_result['file_path'])
                
                # Upload to S3 if configured
                if self.s3_uploader and file_result['file_path']:
                    s3_result = self.s3_uploader.upload_file(
                        file_result['file_path'],
                        f"files/{Path(file_result['file_path']).name}"
                    )
                    backup_results['files_s3'] = s3_result
                    
                    if s3_result['success']:
                        self.logger.info("File backup uploaded to S3")
                    else:
                        self.logger.error(f"S3 upload failed: {s3_result['error']}")
            else:
                self.logger.error(f"File backup failed: {file_result['error']}")
                self.update_status('files', 'failed', file_result['error'])
                
            # Cleanup old backups
            self.logger.info("Cleaning up old backups...")
            self.db_backup.cleanup_old_backups()
            self.file_backup.cleanup_old_backups()
            
            # Check overall success
            core_operations = ['database', 'files']
            successful_operations = sum(1 for op in core_operations if backup_results.get(op, {}).get('success', False))
            
            if successful_operations == len(core_operations):
                self.update_status('backup_cycle', 'success', 'All backup operations completed successfully')
                self.logger.info("=== Backup cycle completed successfully ===")
            else:
                self.update_status('backup_cycle', 'partial', f'{successful_operations}/{len(core_operations)} operations succeeded')
                self.logger.warning("=== Backup cycle completed with errors ===")
                
        except Exception as e:
            self.logger.error(f"Backup cycle failed: {e}")
            self.update_status('backup_cycle', 'failed', str(e))
            
    def schedule_backups(self):
        """Schedule backup jobs based on configuration"""
        # Parse cron schedule (simplified - supports daily backups)
        schedule_parts = self.config['backup_schedule'].split()
        
        if len(schedule_parts) == 5:
            minute, hour = schedule_parts[0], schedule_parts[1]
            
            if minute.isdigit() and hour.isdigit():
                time_str = f"{hour.zfill(2)}:{minute.zfill(2)}"
                schedule.every().day.at(time_str).do(self.run_backup_cycle)
                self.logger.info(f"Backup scheduled daily at {time_str}")
            else:
                # Default fallback
                schedule.every().day.at("02:00").do(self.run_backup_cycle)
                self.logger.info("Using default backup schedule: daily at 02:00")
        else:
            # Default fallback
            schedule.every().day.at("02:00").do(self.run_backup_cycle)
            self.logger.info("Using default backup schedule: daily at 02:00")
            
        # Also allow manual trigger via Redis
        schedule.every(10).seconds.do(self.check_manual_trigger)
        
    def check_manual_trigger(self):
        """Check for manual backup trigger via Redis"""
        if not self.redis_client:
            return
            
        try:
            trigger = self.redis_client.get('backup:manual_trigger')
            if trigger:
                self.redis_client.delete('backup:manual_trigger')
                self.logger.info("Manual backup triggered")
                threading.Thread(target=self.run_backup_cycle).start()
        except Exception as e:
            self.logger.error(f"Error checking manual trigger: {e}")
            
    def get_status(self) -> Dict[str, Any]:
        """Get current backup service status"""
        if not self.redis_client:
            return {"error": "Redis not available"}
            
        try:
            status = {
                "service_running": self.running,
                "last_cycle": None,
                "operations": {}
            }
            
            # Get overall backup cycle status
            cycle_status = self.redis_client.get('backup:status:backup_cycle')
            if cycle_status:
                status["last_cycle"] = json.loads(cycle_status)
                
            # Get individual operation statuses
            for operation in ['database', 'files']:
                op_status = self.redis_client.get(f'backup:status:{operation}')
                last_success = self.redis_client.get(f'backup:last_success:{operation}')
                
                status["operations"][operation] = {
                    "last_status": json.loads(op_status) if op_status else None,
                    "last_success": last_success.decode() if last_success else None
                }
                
            return status
            
        except Exception as e:
            return {"error": str(e)}
            
    def handle_shutdown(self, signum, frame):
        """Handle shutdown signal"""
        self.logger.info("Shutdown signal received")
        self.running = False
        
    def run(self):
        """Main service loop"""
        self.logger.info("Starting Backup Service")
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        # Schedule backups
        self.schedule_backups()
        
        # Mark service as running
        self.running = True
        self.update_status('service', 'running', 'Backup service started')
        
        # Main loop
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self.running = False
            self.update_status('service', 'stopped', 'Backup service stopped')
            self.logger.info("Backup Service stopped")

def main():
    """Main entry point"""
    try:
        service = BackupService()
        service.run()
    except Exception as e:
        logging.error(f"Failed to start backup service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()