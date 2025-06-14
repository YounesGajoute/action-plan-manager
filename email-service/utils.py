# ===================================================================
# email-service/utils.py - Email Service Utilities
# ===================================================================

import re
import hashlib
import base64
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import structlog
from email.utils import parseaddr, formataddr
from urllib.parse import urlparse

logger = structlog.get_logger(__name__)

class EmailValidator:
    """Email validation utilities"""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email address format"""
        if not email or len(email) > 254:
            return False
        
        # Basic regex pattern for email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            return False
        
        # Additional checks
        local, domain = email.rsplit('@', 1)
        
        # Local part checks
        if len(local) > 64 or len(local) == 0:
            return False
        
        # Domain part checks
        if len(domain) > 253 or len(domain) == 0:
            return False
        
        return True
    
    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize email address"""
        if not email:
            return email
        
        email = email.strip().lower()
        
        # Parse email address
        name, addr = parseaddr(email)
        if not addr:
            return email
        
        return addr
    
    @staticmethod
    def extract_domain(email: str) -> Optional[str]:
        """Extract domain from email address"""
        try:
            normalized = EmailValidator.normalize_email(email)
            if '@' in normalized:
                return normalized.split('@')[1]
        except Exception:
            pass
        return None
    
    @staticmethod
    def is_allowed_domain(email: str, allowed_domains: List[str]) -> bool:
        """Check if email domain is in allowed domains list"""
        if not allowed_domains:
            return True
        
        domain = EmailValidator.extract_domain(email)
        if not domain:
            return False
        
        return domain.lower() in [d.lower() for d in allowed_domains]

class ContentSanitizer:
    """Content sanitization utilities"""
    
    @staticmethod
    def sanitize_subject(subject: str, max_length: int = 200) -> str:
        """Sanitize email subject"""
        if not subject:
            return "Notification"
        
        # Remove control characters
        subject = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', subject)
        
        # Remove excessive whitespace
        subject = ' '.join(subject.split())
        
        # Truncate if too long
        if len(subject) > max_length:
            subject = subject[:max_length-3] + "..."
        
        return subject
    
    @staticmethod
    def sanitize_html_content(content: str) -> str:
        """Sanitize HTML content"""
        if not content:
            return ""
        
        # Remove potentially dangerous tags and attributes
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input']
        dangerous_attrs = ['onload', 'onerror', 'onclick', 'onmouseover', 'javascript:']
        
        for tag in dangerous_tags:
            content = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', content, flags=re.IGNORECASE | re.DOTALL)
            content = re.sub(f'<{tag}[^>]*/?>', '', content, flags=re.IGNORECASE)
        
        for attr in dangerous_attrs:
            content = re.sub(f'{attr}[^>]*', '', content, flags=re.IGNORECASE)
        
        return content
    
    @staticmethod
    def extract_text_from_html(html: str) -> str:
        """Extract plain text from HTML"""
        try:
            # Simple HTML to text conversion
            text = re.sub(r'<br[^>]*>', '\n', html, flags=re.IGNORECASE)
            text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(r'<[^>]+>', '', text)
            
            # Decode HTML entities
            text = text.replace('&nbsp;', ' ')
            text = text.replace('&amp;', '&')
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&quot;', '"')
            text = text.replace('&#39;', "'")
            
            # Clean up whitespace
            text = '\n'.join(line.strip() for line in text.split('\n'))
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            return text.strip()
        except Exception as e:
            logger.error("Failed to extract text from HTML", error=str(e))
            return ""

class AttachmentHandler:
    """Attachment handling utilities"""
    
    @staticmethod
    def is_allowed_file_type(filename: str, allowed_types: List[str]) -> bool:
        """Check if file type is allowed"""
        if not allowed_types:
            return True
        
        file_ext = Path(filename).suffix.lower().lstrip('.')
        return file_ext in [ext.lower() for ext in allowed_types]
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return Path(file_path).stat().st_size
        except Exception:
            return 0
    
    @staticmethod
    def is_file_size_allowed(file_path: str, max_size: int) -> bool:
        """Check if file size is within limits"""
        return AttachmentHandler.get_file_size(file_path) <= max_size
    
    @staticmethod
    def get_mime_type(filename: str) -> str:
        """Get MIME type for file"""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'
    
    @staticmethod
    def validate_attachment(file_path: str, allowed_types: List[str], max_size: int) -> Tuple[bool, str]:
        """Validate attachment file"""
        if not Path(file_path).exists():
            return False, "File does not exist"
        
        filename = Path(file_path).name
        
        if not AttachmentHandler.is_allowed_file_type(filename, allowed_types):
            return False, f"File type not allowed. Allowed types: {', '.join(allowed_types)}"
        
        if not AttachmentHandler.is_file_size_allowed(file_path, max_size):
            size_mb = AttachmentHandler.get_file_size(file_path) / (1024 * 1024)
            max_mb = max_size / (1024 * 1024)
            return False, f"File too large ({size_mb:.1f}MB). Maximum size: {max_mb:.1f}MB"
        
        return True, "Valid attachment"

class RateLimiter:
    """Rate limiting utilities"""
    
    def __init__(self, redis_client, prefix: str = "email_rate_limit"):
        self.redis_client = redis_client
        self.prefix = prefix
    
    def is_rate_limited(self, identifier: str, limit: int, window: int) -> bool:
        """Check if identifier is rate limited"""
        try:
            key = f"{self.prefix}:{identifier}"
            current = self.redis_client.get(key)
            
            if current is None:
                # First request in window
                self.redis_client.setex(key, window, 1)
                return False
            
            if int(current) >= limit:
                return True
            
            # Increment counter
            self.redis_client.incr(key)
            return False
        
        except Exception as e:
            logger.error("Rate limiting check failed", error=str(e))
            # Fail open - allow request if rate limiting fails
            return False
    
    def get_rate_limit_info(self, identifier: str, window: int) -> Dict[str, Any]:
        """Get rate limit information"""
        try:
            key = f"{self.prefix}:{identifier}"
            current = self.redis_client.get(key)
            ttl = self.redis_client.ttl(key)
            
            return {
                'current_count': int(current) if current else 0,
                'reset_time': datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None,
                'window_seconds': window
            }
        except Exception as e:
            logger.error("Failed to get rate limit info", error=str(e))
            return {'current_count': 0, 'reset_time': None, 'window_seconds': window}

class TemplateCache:
    """Template caching utilities"""
    
    def __init__(self, redis_client, cache_ttl: int = 3600):
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
        self.prefix = "email_template_cache"
    
    def get_cache_key(self, template_name: str, language: str) -> str:
        """Generate cache key for template"""
        return f"{self.prefix}:{template_name}:{language}"
    
    def get_cached_template(self, template_name: str, language: str) -> Optional[Tuple[str, str]]:
        """Get cached template"""
        try:
            key = self.get_cache_key(template_name, language)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                import json
                data = json.loads(cached_data)
                return data.get('html'), data.get('text')
        except Exception as e:
            logger.error("Failed to get cached template", error=str(e))
        
        return None
    
    def cache_template(self, template_name: str, language: str, html_content: str, text_content: str):
        """Cache template content"""
        try:
            import json
            key = self.get_cache_key(template_name, language)
            data = {
                'html': html_content,
                'text': text_content,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis_client.setex(key, self.cache_ttl, json.dumps(data))
        except Exception as e:
            logger.error("Failed to cache template", error=str(e))
    
    def invalidate_template_cache(self, template_name: str, language: str = None):
        """Invalidate template cache"""
        try:
            if language:
                key = self.get_cache_key(template_name, language)
                self.redis_client.delete(key)
            else:
                # Invalidate all languages for this template
                pattern = f"{self.prefix}:{template_name}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
        except Exception as e:
            logger.error("Failed to invalidate template cache", error=str(e))

class EmailMetrics:
    """Email metrics utilities"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.prefix = "email_metrics"
    
    def increment_sent_count(self, template_name: str = None):
        """Increment sent email count"""
        try:
            self.redis_client.incr(f"{self.prefix}:sent:total")
            if template_name:
                self.redis_client.incr(f"{self.prefix}:sent:template:{template_name}")
        except Exception as e:
            logger.error("Failed to increment sent count", error=str(e))
    
    def increment_failed_count(self, template_name: str = None, error_type: str = None):
        """Increment failed email count"""
        try:
            self.redis_client.incr(f"{self.prefix}:failed:total")
            if template_name:
                self.redis_client.incr(f"{self.prefix}:failed:template:{template_name}")
            if error_type:
                self.redis_client.incr(f"{self.prefix}:failed:type:{error_type}")
        except Exception as e:
            logger.error("Failed to increment failed count", error=str(e))
    
    def record_send_time(self, duration_ms: float, template_name: str = None):
        """Record email send time"""
        try:
            # Store as sorted set for percentile calculations
            timestamp = datetime.utcnow().timestamp()
            self.redis_client.zadd(f"{self.prefix}:send_times", {timestamp: duration_ms})
            
            if template_name:
                self.redis_client.zadd(f"{self.prefix}:send_times:template:{template_name}", 
                                     {timestamp: duration_ms})
            
            # Keep only last 1000 measurements
            self.redis_client.zremrangebyrank(f"{self.prefix}:send_times", 0, -1001)
        except Exception as e:
            logger.error("Failed to record send time", error=str(e))
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        try:
            return {
                'total_sent': int(self.redis_client.get(f"{self.prefix}:sent:total") or 0),
                'total_failed': int(self.redis_client.get(f"{self.prefix}:failed:total") or 0),
                'avg_send_time': self._get_avg_send_time(),
                'last_24h_sent': self._get_count_last_24h('sent'),
                'last_24h_failed': self._get_count_last_24h('failed')
            }
        except Exception as e:
            logger.error("Failed to get metrics summary", error=str(e))
            return {}
    
    def _get_avg_send_time(self) -> float:
        """Get average send time"""
        try:
            times = self.redis_client.zrange(f"{self.prefix}:send_times", 0, -1, withscores=True)
            if times:
                total_time = sum(score for _, score in times)
                return total_time / len(times)
        except Exception:
            pass
        return 0.0
    
    def _get_count_last_24h(self, metric_type: str) -> int:
        """Get count for last 24 hours"""
        # This is a simplified implementation
        # In a real scenario, you'd store timestamped data
        return 0

class URLSafetyChecker:
    """URL safety checking utilities"""
    
    @staticmethod
    def is_safe_url(url: str, allowed_domains: List[str] = None) -> bool:
        """Check if URL is safe"""
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check domain if allowed_domains is specified
            if allowed_domains:
                domain = parsed.netloc.lower()
                return any(domain.endswith(allowed_domain.lower()) 
                          for allowed_domain in allowed_domains)
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def sanitize_url(url: str) -> str:
        """Sanitize URL"""
        try:
            parsed = urlparse(url)
            # Reconstruct URL with only safe components
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        except Exception:
            return ""

class EmailDeduplicator:
    """Email deduplication utilities"""
    
    def __init__(self, redis_client, ttl: int = 3600):
        self.redis_client = redis_client
        self.ttl = ttl
        self.prefix = "email_dedup"
    
    def generate_email_hash(self, to_email: str, subject: str, content_hash: str) -> str:
        """Generate hash for email deduplication"""
        content = f"{to_email}:{subject}:{content_hash}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_duplicate(self, email_hash: str) -> bool:
        """Check if email is duplicate"""
        try:
            key = f"{self.prefix}:{email_hash}"
            return self.redis_client.exists(key)
        except Exception as e:
            logger.error("Failed to check duplicate", error=str(e))
            return False
    
    def mark_as_sent(self, email_hash: str):
        """Mark email as sent"""
        try:
            key = f"{self.prefix}:{email_hash}"
            self.redis_client.setex(key, self.ttl, datetime.utcnow().isoformat())
        except Exception as e:
            logger.error("Failed to mark as sent", error=str(e))

class ContentHasher:
    """Content hashing utilities"""
    
    @staticmethod
    def hash_content(content: str) -> str:
        """Generate hash for content"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @staticmethod
    def hash_template_context(context: Dict) -> str:
        """Generate hash for template context"""
        import json
        # Sort keys for consistent hashing
        sorted_context = json.dumps(context, sort_keys=True, default=str)
        return ContentHasher.hash_content(sorted_context)

def format_email_address(email: str, name: str = None) -> str:
    """Format email address with optional name"""
    if name:
        return formataddr((name, email))
    return email

def parse_email_address(email_str: str) -> Tuple[str, str]:
    """Parse email address string into name and email"""
    name, email = parseaddr(email_str)
    return name or "", email or ""

def get_email_priority_header(priority: str) -> Dict[str, str]:
    """Get email priority headers"""
    priority_map = {
        'high': {'X-Priority': '1', 'X-MSMail-Priority': 'High', 'Importance': 'high'},
        'normal': {'X-Priority': '3', 'X-MSMail-Priority': 'Normal', 'Importance