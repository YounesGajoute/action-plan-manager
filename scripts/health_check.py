import psutil
import requests
import docker
import redis
import psycopg2
from dataclasses import dataclass
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    message: str
    details: Dict = None
    response_time: float = 0.0

class SystemHealthChecker:
    """Comprehensive system health monitoring"""
    
    def __init__(self):
        self.checks = []
        self.docker_client = None
        
        try:
            self.docker_client = docker.from_env()
        except Exception:
            logger.warning("Docker client not available")
            
    def run_all_checks(self) -> List[HealthCheck]:
        """Run all health checks"""
        self.checks = []
        
        # System checks
        self.checks.append(self._check_system_resources())
        self.checks.append(self._check_disk_space())
        
        # Service checks
        self.checks.append(self._check_database())
        self.checks.append(self._check_redis())
        self.checks.append(self._check_api_service())
        self.checks.append(self._check_frontend_service())
        
        # Docker checks
        if self.docker_client:
            self.checks.extend(self._check_docker_containers())
            
        return self.checks
        
    def _check_system_resources(self) -> HealthCheck:
        """Check CPU and memory usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            details = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
            }
            
            if cpu_percent > 90 or memory.percent > 90:
                status = HealthStatus.CRITICAL
                message = f"High resource usage: CPU {cpu_percent}%, Memory {memory.percent}%"
            elif cpu_percent > 70 or memory.percent > 70:
                status = HealthStatus.WARNING
                message = f"Moderate resource usage: CPU {cpu_percent}%, Memory {memory.percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Resource usage normal: CPU {cpu_percent}%, Memory {memory.percent}%"
                
            return HealthCheck("System Resources", status, message, details)
            
        except Exception as e:
            return HealthCheck("System Resources", HealthStatus.UNKNOWN, str(e))
            
    def _check_disk_space(self) -> HealthCheck:
        """Check disk space usage"""
        try:
            disk = psutil.disk_usage('/')
            
            details = {
                'total_gb': disk.total / (1024**3),
                'used_gb': disk.used / (1024**3),
                'free_gb': disk.free / (1024**3),
                'percent_used': (disk.used / disk.total) * 100
            }
            
            percent_used = details['percent_used']
            
            if percent_used > 95:
                status = HealthStatus.CRITICAL
                message = f"Disk space critically low: {percent_used:.1f}% used"
            elif percent_used > 85:
                status = HealthStatus.WARNING
                message = f"Disk space running low: {percent_used:.1f}% used"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space sufficient: {percent_used:.1f}% used"
                
            return HealthCheck("Disk Space", status, message, details)
            
        except Exception as e:
            return HealthCheck("Disk Space", HealthStatus.UNKNOWN, str(e))
            
    def _check_database(self) -> HealthCheck:
        """Check PostgreSQL database connection"""
        try:
            start_time = datetime.now()
            
            # Get database URL from environment
            db_url = os.getenv('DATABASE_URL', 'postgresql://actionplan:password@localhost:5432/actionplan')
            
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Test query
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            # Get database stats
            cursor.execute("""
                SELECT 
                    pg_database_size(current_database()) as db_size,
                    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections
            """)
            db_size, active_connections = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            details = {
                'database_size_mb': db_size / (1024**2) if db_size else 0,
                'active_connections': active_connections,
                'response_time_ms': response_time * 1000
            }
            
            if response_time > 2.0:
                status = HealthStatus.WARNING
                message = f"Database slow response: {response_time:.2f}s"
            else:
                status = HealthStatus.HEALTHY
                message = f"Database healthy: {response_time:.3f}s response"
                
            return HealthCheck("Database", status, message, details, response_time)
            
        except Exception as e:
            return HealthCheck("Database", HealthStatus.CRITICAL, str(e))
            
    def _check_redis(self) -> HealthCheck:
        """Check Redis connection"""
        try:
            start_time = datetime.now()
            
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            r = redis.from_url(redis_url)
            
            # Test connection
            r.ping()
            
            # Get Redis info
            info = r.info()
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            details = {
                'used_memory_mb': info.get('used_memory', 0) / (1024**2),
                'connected_clients': info.get('connected_clients', 0),
                'uptime_seconds': info.get('uptime_in_seconds', 0),
                'response_time_ms': response_time * 1000
            }
            
            if response_time > 1.0:
                status = HealthStatus.WARNING
                message = f"Redis slow response: {response_time:.2f}s"
            else:
                status = HealthStatus.HEALTHY
                message = f"Redis healthy: {response_time:.3f}s response"
                
            return HealthCheck("Redis", status, message, details, response_time)
            
        except Exception as e:
            return HealthCheck("Redis", HealthStatus.CRITICAL, str(e))
            
    def _check_api_service(self) -> HealthCheck:
        """Check API service health"""
        try:
            start_time = datetime.now()
            
            api_url = os.getenv('API_URL', 'http://localhost:5000')
            response = requests.get(f"{api_url}/health", timeout=10)
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            details = {
                'status_code': response.status_code,
                'response_time_ms': response_time * 1000,
                'url': f"{api_url}/health"
            }
            
            if response.status_code == 200:
                if response_time > 2.0:
                    status = HealthStatus.WARNING
                    message = f"API slow response: {response_time:.2f}s"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"API healthy: {response_time:.3f}s response"
            else:
                status = HealthStatus.CRITICAL
                message = f"API unhealthy: HTTP {response.status_code}"
                
            return HealthCheck("API Service", status, message, details, response_time)
            
        except Exception as e:
            return HealthCheck("API Service", HealthStatus.CRITICAL, str(e))
            
    def _check_frontend_service(self) -> HealthCheck:
        """Check frontend service health"""
        try:
            start_time = datetime.now()
            
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
            response = requests.get(frontend_url, timeout=10)
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            details = {
                'status_code': response.status_code,
                'response_time_ms': response_time * 1000,
                'url': frontend_url
            }
            
            if response.status_code == 200:
                if response_time > 3.0:
                    status = HealthStatus.WARNING
                    message = f"Frontend slow response: {response_time:.2f}s"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Frontend healthy: {response_time:.3f}s response"
            else:
                status = HealthStatus.CRITICAL
                message = f"Frontend unhealthy: HTTP {response.status_code}"
                
            return HealthCheck("Frontend Service", status, message, details, response_time)
            
        except Exception as e:
            return HealthCheck("Frontend Service", HealthStatus.CRITICAL, str(e))
            
    def _check_docker_containers(self) -> List[HealthCheck]:
        """Check Docker container health"""
        checks = []
        
        try:
            containers = self.docker_client.containers.list(all=True)
            
            for container in containers:
                try:
                    details = {
                        'image': container.image.tags[0] if container.image.tags else 'unknown',
                        'status': container.status,
                        'created': container.attrs['Created'],
                        'ports': container.ports
                    }
                    
                    if container.status == 'running':
                        # Check if container is healthy
                        health = container.attrs.get('State', {}).get('Health', {})
                        if health:
                            health_status = health.get('Status', 'unknown')
                            if health_status == 'healthy':
                                status = HealthStatus.HEALTHY
                                message = "Container running and healthy"
                            elif health_status == 'unhealthy':
                                status = HealthStatus.CRITICAL
                                message = "Container running but unhealthy"
                            else:
                                status = HealthStatus.WARNING
                                message = f"Container health status: {health_status}"
                        else:
                            status = HealthStatus.HEALTHY
                            message = "Container running (no health check)"
                    elif container.status in ['exited', 'dead']:
                        status = HealthStatus.CRITICAL
                        message = f"Container {container.status}"
                    else:
                        status = HealthStatus.WARNING
                        message = f"Container status: {container.status}"
                        
                    checks.append(HealthCheck(
                        f"Container: {container.name}",
                        status,
                        message,
                        details
                    ))
                    
                except Exception as e:
                    checks.append(HealthCheck(
                        f"Container: {container.name}",
                        HealthStatus.UNKNOWN,
                        str(e)
                    ))
                    
        except Exception as e:
            checks.append(HealthCheck("Docker Containers", HealthStatus.UNKNOWN, str(e)))
            
        return checks
        
    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status"""
        if not self.checks:
            return HealthStatus.UNKNOWN
            
        critical_count = sum(1 for check in self.checks if check.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for check in self.checks if check.status == HealthStatus.WARNING)
        
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif warning_count > 0:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
            
    def generate_report(self) -> str:
        """Generate health check report"""
        overall_status = self.get_overall_status()
        
        report = f"🏥 **System Health Report**\n"
        report += f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"🎯 Overall Status: {overall_status.value.upper()}\n\n"
        
        # Group checks by status
        status_groups = {
            HealthStatus.HEALTHY: [],
            HealthStatus.WARNING: [],
            HealthStatus.CRITICAL: [],
            HealthStatus.UNKNOWN: []
        }
        
        for check in self.checks:
            status_groups[check.status].append(check)
            
        # Report by status
        status_icons = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.WARNING: "⚠️",
            HealthStatus.CRITICAL: "❌",
            HealthStatus.UNKNOWN: "❓"
        }
        
        for status, checks in status_groups.items():
            if checks:
                report += f"\n{status_icons[status]} **{status.value.upper()} ({len(checks)})**\n"
                for check in checks:
                    report += f"  • {check.name}: {check.message}\n"
                    if check.response_time > 0:
                        report += f"    Response time: {check.response_time:.3f}s\n"
                        
        return report

# ===================================================================
# Main CLI Functions
# ===================================================================

def cleanup_logs_main():
    """CLI for log cleanup"""
    parser = argparse.ArgumentParser(description='Clean up and rotate log files')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--stats', action='store_true', help='Show log statistics only')
    
    args = parser.parse_args()
    
    cleaner = LogCleaner(args.config)
    
    if args.stats:
        stats = cleaner.get_log_statistics()
        print("📊 Log Statistics:")
        print(f"Total files: {stats['total_files']}")
        print(f"Total size: {stats['total_size'] / (1024**3):.2f} GB")
        print(f"Compressed files: {stats['compressed_files']}")
        
        if stats['oldest_file']:
            print(f"Oldest file: {stats['oldest_file'][0]} ({stats['oldest_file'][1]})")
        if stats['largest_file']:
            print(f"Largest file: {stats['largest_file'][0]} ({stats['largest_file'][1] / (1024**2):.1f} MB)")
            
        for directory, dir_stats in stats['directories'].items():
            print(f"\n📁 {directory}:")
            print(f"  Files: {dir_stats['files']}")
            print(f"  Size: {dir_stats['size'] / (1024**2):.1f} MB")
            print(f"  Compressed: {dir_stats['compressed']}")
    else:
        result = cleaner.cleanup_logs(args.dry_run)
        
        print("🧹 Log Cleanup Results:")
        print(f"Files processed: {result['files_processed']}")
        print(f"Files compressed: {result['files_compressed']}")
        print(f"Files deleted: {result['files_deleted']}")
        print(f"Space saved: {result['bytes_saved'] / (1024**2):.1f} MB")
        
        if result['errors']:
            print(f"\n❌ Errors ({len(result['errors'])}):")
            for error in result['errors']:
                print(f"  {error}")

def health_check_main():
    """CLI for health checks"""
    parser = argparse.ArgumentParser(description='System health monitoring')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    parser.add_argument('--checks', nargs='+', help='Specific checks to run')
    
    args = parser.parse_args()
    
    checker = SystemHealthChecker()
    checks = checker.run_all_checks()
    
    if args.format == 'json':
        result = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': checker.get_overall_status().value,
            'checks': [
                {
                    'name': check.name,
                    'status': check.status.value,
                    'message': check.message,
                    'details': check.details,
                    'response_time': check.response_time
                }
                for check in checks
            ]
        }
        print(json.dumps(result, indent=2))
    else:
        print(checker.generate_report())
        
    # Exit with appropriate code
    overall_status = checker.get_overall_status()
    if overall_status == HealthStatus.CRITICAL:
        sys.exit(2)
    elif overall_status == HealthStatus.WARNING:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    if 'cleanup' in sys.argv[0]:
        cleanup_logs_main()
    elif 'health' in sys.argv[0]:
        health_check_main()
    else:
        print("Usage:")
        print("  python scripts/cleanup_logs.py [options]")
        print("  python scripts/health_check.py [options]")
        print("\nUse --help for detailed options")