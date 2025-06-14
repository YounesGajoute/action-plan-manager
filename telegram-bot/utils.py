# ===================================================================
# telegram-bot/utils.py
# ===================================================================
import json
import logging
import re
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from functools import wraps
import aiohttp
import requests
from telegram import Update, User, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import pytz
from config import settings, BotMessages
import jwt
from cryptography.fernet import Fernet


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class APIClient:
    """HTTP client for API communication"""
    
    def __init__(self):
        self.base_url = settings.api_base_url.rstrip('/')
        self.timeout = settings.api_timeout
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        
        default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TechMac-TelegramBot/1.0'
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                headers=default_headers,
                json=data,
                params=params
            ) as response:
                response_data = await response.json()
                
                if response.status >= 400:
                    logger.error(f"API Error {response.status}: {response_data}")
                    raise APIException(f"API Error: {response_data.get('error', 'Unknown error')}")
                
                return response_data
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP Client Error: {e}")
            raise APIException(f"Connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise APIException(f"Unexpected error: {str(e)}")
    
    async def get(self, endpoint: str, headers: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        return await self._make_request('GET', endpoint, headers, params=params)
    
    async def post(self, endpoint: str, data: Dict, headers: Optional[Dict] = None) -> Dict:
        return await self._make_request('POST', endpoint, headers, data)
    
    async def put(self, endpoint: str, data: Dict, headers: Optional[Dict] = None) -> Dict:
        return await self._make_request('PUT', endpoint, headers, data)
    
    async def delete(self, endpoint: str, headers: Optional[Dict] = None) -> Dict:
        return await self._make_request('DELETE', endpoint, headers)


class UserSession:
    """User session management"""
    
    def __init__(self):
        self.sessions: Dict[int, Dict] = {}
        self.encryption = Fernet(settings.encryption_key.encode()[:32].ljust(32, b'0'))
    
    def create_session(self, user_id: int, user_data: Dict) -> str:
        """Create a new user session"""
        session_data = {
            'user_id': user_id,
            'user_data': user_data,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expires_at': (datetime.now(timezone.utc) + timedelta(seconds=settings.session_timeout)).isoformat()
        }
        
        # Encrypt session data
        encrypted_data = self.encryption.encrypt(json.dumps(session_data).encode())
        
        # Store in memory (in production, use Redis)
        self.sessions[user_id] = {
            'encrypted_data': encrypted_data,
            'last_activity': datetime.now(timezone.utc)
        }
        
        return encrypted_data.hex()
    
    def get_session(self, user_id: int) -> Optional[Dict]:
        """Get user session data"""
        if user_id not in self.sessions:
            return None
        
        session = self.sessions[user_id]
        
        # Check if session is expired
        if datetime.now(timezone.utc) - session['last_activity'] > timedelta(seconds=settings.session_timeout):
            del self.sessions[user_id]
            return None
        
        try:
            # Decrypt session data
            decrypted_data = self.encryption.decrypt(session['encrypted_data'])
            session_data = json.loads(decrypted_data.decode())
            
            # Update last activity
            session['last_activity'] = datetime.now(timezone.utc)
            
            return session_data
        except Exception as e:
            logger.error(f"Error decrypting session: {e}")
            return None
    
    def update_session(self, user_id: int, data: Dict) -> bool:
        """Update user session data"""
        session_data = self.get_session(user_id)
        if not session_data:
            return False
        
        session_data.update(data)
        self.sessions[user_id]['encrypted_data'] = self.encryption.encrypt(
            json.dumps(session_data).encode()
        )
        return True
    
    def delete_session(self, user_id: int) -> bool:
        """Delete user session"""
        if user_id in self.sessions:
            del self.sessions[user_id]
            return True
        return False


class RateLimiter:
    """Rate limiting for user requests"""
    
    def __init__(self):
        self.user_requests: Dict[int, List[datetime]] = {}
    
    def is_rate_limited(self, user_id: int) -> bool:
        """Check if user is rate limited"""
        now = datetime.now()
        window_start = now - timedelta(seconds=settings.rate_limit_window)
        
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        
        # Clean old requests
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if req_time > window_start
        ]
        
        # Check rate limit
        if len(self.user_requests[user_id]) >= settings.rate_limit_per_user:
            return True
        
        # Add current request
        self.user_requests[user_id].append(now)
        return False


# Global instances
api_client = APIClient()
user_session = UserSession()
rate_limiter = RateLimiter()


class APIException(Exception):
    """Custom exception for API errors"""
    pass


class AuthenticationError(Exception):
    """Authentication related errors"""
    pass


def require_auth(func):
    """Decorator to require user authentication"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        session_data = user_session.get_session(user_id)
        
        if not session_data:
            await update.message.reply_text(
                "🔐 Vous devez vous connecter pour utiliser cette fonctionnalité.\n"
                "Utilisez /start pour commencer l'authentification."
            )
            return
        
        # Add session data to context
        context.user_data['session'] = session_data
        return await func(update, context)
    
    return wrapper


def require_admin(func):
    """Decorator to require admin privileges"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        # Check if user is admin
        if str(user_id) not in settings.admin_users and username not in settings.admin_users:
            await update.message.reply_text(BotMessages.ERROR_UNAUTHORIZED)
            return
        
        return await func(update, context)
    
    return wrapper


def rate_limit(func):
    """Decorator to apply rate limiting"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if rate_limiter.is_rate_limited(user_id):
            await update.message.reply_text(BotMessages.ERROR_RATE_LIMIT)
            return
        
        return await func(update, context)
    
    return wrapper


def format_datetime(dt: Union[str, datetime], user_timezone: str = None) -> str:
    """Format datetime for display"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    
    if user_timezone:
        try:
            tz = pytz.timezone(user_timezone)
            dt = dt.astimezone(tz)
        except pytz.UnknownTimeZoneError:
            pass
    
    return dt.strftime('%d/%m/%Y %H:%M')


def format_task_status(status: str) -> str:
    """Format task status with emoji"""
    status_emojis = {
        'En Attente': '⏳',
        'En Cours': '🔄',
        'Terminé': '✅',
        'Annulé': '❌',
        'En Pause': '⏸️'
    }
    return f"{status_emojis.get(status, '❓')} {status}"


def format_task_priority(priority: str) -> str:
    """Format task priority with emoji"""
    priority_emojis = {
        'Urgent': '🔴',
        'Élevé': '🟠',
        'Moyen': '🟡',
        'Faible': '🟢'
    }
    return f"{priority_emojis.get(priority, '⚪')} {priority}"


def format_task_category(category: str) -> str:
    """Format task category with emoji"""
    category_emojis = {
        'Installation': '🔧',
        'Réparation': '🛠️',
        'Développement': '💻',
        'Livraison': '🚚',
        'Commercial': '💼'
    }
    return f"{category_emojis.get(category, '📋')} {category}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def create_pagination_keyboard(
    items: List[Dict],
    page: int,
    items_per_page: int,
    callback_prefix: str
) -> InlineKeyboardMarkup:
    """Create pagination keyboard"""
    total_pages = (len(items) + items_per_page - 1) // items_per_page
    
    keyboard = []
    
    # Navigation buttons
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("⬅️ Précédent", callback_data=f"{callback_prefix}_page_{page-1}")
        )
    
    nav_buttons.append(
        InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop")
    )
    
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton("Suivant ➡️", callback_data=f"{callback_prefix}_page_{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(keyboard)


def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


def validate_po_number(po_number: str) -> bool:
    """Validate PO number format"""
    return bool(re.match(r'^[A-Z0-9-]+$', po_number.upper()))


def validate_email(email: str) -> bool:
    """Validate email format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def format_task_summary(task: Dict) -> str:
    """Format task summary for display"""
    summary = f"**📋 {task.get('po_number', 'N/A')}**\n"
    summary += f"📝 {truncate_text(task.get('action_description', ''), 80)}\n"
    summary += f"👤 {task.get('customer', 'N/A')}\n"
    summary += f"👷 {task.get('responsible', 'N/A')}\n"
    summary += f"📊 {format_task_status(task.get('status', 'N/A'))}\n"
    
    if task.get('priority'):
        summary += f"⚡ {format_task_priority(task['priority'])}\n"
    
    if task.get('category'):
        summary += f"🏷️ {format_task_category(task['category'])}\n"
    
    if task.get('deadline'):
        deadline = format_datetime(task['deadline'])
        summary += f"⏰ Échéance: {deadline}\n"
    
    return summary


def format_statistics(stats: Dict) -> str:
    """Format statistics for display"""
    message = "📊 **Statistiques des Tâches**\n\n"
    
    # Task counts
    if 'task_counts' in stats:
        counts = stats['task_counts']
        message += f"📈 **Totaux:**\n"
        message += f"• Total: {counts.get('total', 0)}\n"
        message += f"• En cours: {counts.get('in_progress', 0)}\n"
        message += f"• Terminées: {counts.get('completed', 0)}\n"
        message += f"• En attente: {counts.get('pending', 0)}\n"
        message += f"• En retard: {counts.get('overdue', 0)}\n\n"
    
    # Completion rate
    if 'completion_rate' in stats:
        rate = stats['completion_rate']
        message += f"✅ **Taux de complétion:** {rate:.1f}%\n\n"
    
    # Category breakdown
    if 'by_category' in stats:
        message += f"🏷️ **Par catégorie:**\n"
        for category, count in stats['by_category'].items():
            message += f"• {format_task_category(category)}: {count}\n"
    
    return message


async def send_long_message(
    update: Update,
    message: str,
    parse_mode: str = None,
    reply_markup=None
) -> None:
    """Send long message, splitting if necessary"""
    max_length = settings.max_message_length
    
    if len(message) <= max_length:
        await update.message.reply_text(
            message, 
            parse_mode=parse_mode, 
            reply_markup=reply_markup
        )
        return
    
    # Split message into chunks
    chunks = []
    current_chunk = ""
    
    for line in message.split('\n'):
        if len(current_chunk + line + '\n') > max_length:
            if current_chunk:
                chunks.append(current_chunk.rstrip())
                current_chunk = line + '\n'
            else:
                # Line too long, force split
                chunks.append(line[:max_length])
                current_chunk = line[max_length:] + '\n'
        else:
            current_chunk += line + '\n'
    
    if current_chunk:
        chunks.append(current_chunk.rstrip())
    
    # Send chunks
    for i, chunk in enumerate(chunks):
        is_last = i == len(chunks) - 1
        await update.message.reply_text(
            chunk,
            parse_mode=parse_mode,
            reply_markup=reply_markup if is_last else None
        )


class TaskManager:
    """Task management helper class"""
    
    @staticmethod
    async def get_user_tasks(user_id: int, filters: Dict = None) -> List[Dict]:
        """Get tasks for a user"""
        try:
            session_data = user_session.get_session(user_id)
            if not session_data:
                raise AuthenticationError("User not authenticated")
            
            # Get user token from session
            user_token = session_data.get('access_token')
            if not user_token:
                raise AuthenticationError("No access token found")
            
            headers = {
                'Authorization': f"Bearer {user_token}"
            }
            
            params = filters or {}
            
            async with APIClient() as client:
                response = await client.get('/api/tasks', headers=headers, params=params)
                return response.get('tasks', [])
                
        except Exception as e:
            logger.error(f"Error getting user tasks: {e}")
            raise
    
    @staticmethod
    async def create_task(user_id: int, task_data: Dict) -> Dict:
        """Create a new task"""
        try:
            session_data = user_session.get_session(user_id)
            if not session_data:
                raise AuthenticationError("User not authenticated")
            
            user_token = session_data.get('access_token')
            headers = {
                'Authorization': f"Bearer {user_token}"
            }
            
            async with APIClient() as client:
                response = await client.post('/api/tasks', task_data, headers=headers)
                return response
                
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise
    
    @staticmethod
    async def update_task(user_id: int, task_id: str, updates: Dict) -> Dict:
        """Update an existing task"""
        try:
            session_data = user_session.get_session(user_id)
            if not session_data:
                raise AuthenticationError("User not authenticated")
            
            user_token = session_data.get('access_token')
            headers = {
                'Authorization': f"Bearer {user_token}"
            }
            
            async with APIClient() as client:
                response = await client.put(f'/api/tasks/{task_id}', updates, headers=headers)
                return response
                
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            raise
    
    @staticmethod
    async def get_task_details(user_id: int, task_id: str) -> Dict:
        """Get detailed information about a task"""
        try:
            session_data = user_session.get_session(user_id)
            if not session_data:
                raise AuthenticationError("User not authenticated")
            
            user_token = session_data.get('access_token')
            headers = {
                'Authorization': f"Bearer {user_token}"
            }
            
            async with APIClient() as client:
                response = await client.get(f'/api/tasks/{task_id}', headers=headers)
                return response
                
        except Exception as e:
            logger.error(f"Error getting task details: {e}")
            raise
    
    @staticmethod
    async def delete_task(user_id: int, task_id: str) -> bool:
        """Delete a task"""
        try:
            session_data = user_session.get_session(user_id)
            if not session_data:
                raise AuthenticationError("User not authenticated")
            
            user_token = session_data.get('access_token')
            headers = {
                'Authorization': f"Bearer {user_token}"
            }
            
            async with APIClient() as client:
                await client.delete(f'/api/tasks/{task_id}', headers=headers)
                return True
                
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            raise
    
    @staticmethod
    async def search_tasks(user_id: int, search_term: str) -> List[Dict]:
        """Search tasks by term"""
        try:
            filters = {
                'search': search_term,
                'limit': 20
            }
            return await TaskManager.get_user_tasks(user_id, filters)
                
        except Exception as e:
            logger.error(f"Error searching tasks: {e}")
            raise
    
    @staticmethod
    async def get_overdue_tasks(user_id: int) -> List[Dict]:
        """Get overdue tasks for user"""
        try:
            filters = {
                'overdue': True
            }
            return await TaskManager.get_user_tasks(user_id, filters)
                
        except Exception as e:
            logger.error(f"Error getting overdue tasks: {e}")
            raise


class AnalyticsManager:
    """Analytics and reporting helper class"""
    
    @staticmethod
    async def get_dashboard_stats(user_id: int) -> Dict:
        """Get dashboard statistics"""
        try:
            session_data = user_session.get_session(user_id)
            if not session_data:
                raise AuthenticationError("User not authenticated")
            
            user_token = session_data.get('access_token')
            headers = {
                'Authorization': f"Bearer {user_token}"
            }
            
            async with APIClient() as client:
                response = await client.get('/api/analytics/dashboard', headers=headers)
                return response
                
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            raise
    
    @staticmethod
    async def get_user_performance(user_id: int, period: str = 'month') -> Dict:
        """Get user performance metrics"""
        try:
            session_data = user_session.get_session(user_id)
            if not session_data:
                raise AuthenticationError("User not authenticated")
            
            user_token = session_data.get('access_token')
            headers = {
                'Authorization': f"Bearer {user_token}"
            }
            
            params = {'period': period}
            
            async with APIClient() as client:
                response = await client.get('/api/analytics/performance', headers=headers, params=params)
                return response
                
        except Exception as e:
            logger.error(f"Error getting user performance: {e}")
            raise


class NotificationManager:
    """Notification management helper class"""
    
    @staticmethod
    async def get_user_notifications(user_id: int, unread_only: bool = False) -> List[Dict]:
        """Get user notifications"""
        try:
            session_data = user_session.get_session(user_id)
            if not session_data:
                raise AuthenticationError("User not authenticated")
            
            user_token = session_data.get('access_token')
            headers = {
                'Authorization': f"Bearer {user_token}"
            }
            
            params = {}
            if unread_only:
                params['unread'] = True
            
            async with APIClient() as client:
                response = await client.get('/api/notifications', headers=headers, params=params)
                return response.get('notifications', [])
                
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            raise
    
    @staticmethod
    async def mark_notification_read(user_id: int, notification_id: str) -> bool:
        """Mark notification as read"""
        try:
            session_data = user_session.get_session(user_id)
            if not session_data:
                raise AuthenticationError("User not authenticated")
            
            user_token = session_data.get('access_token')
            headers = {
                'Authorization': f"Bearer {user_token}"
            }
            
            async with APIClient() as client:
                await client.put(f'/api/notifications/{notification_id}/read', {}, headers=headers)
                return True
                
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            raise


class FileManager:
    """File upload and management helper class"""
    
    @staticmethod
    async def upload_excel_file(user_id: int, file_data: bytes, filename: str) -> Dict:
        """Upload Excel file for task import"""
        try:
            session_data = user_session.get_session(user_id)
            if not session_data:
                raise AuthenticationError("User not authenticated")
            
            user_token = session_data.get('access_token')
            
            # Use requests for file upload (simpler than aiohttp for multipart)
            headers = {
                'Authorization': f"Bearer {user_token}"
            }
            
            files = {
                'file': (filename, file_data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            
            response = requests.post(
                f"{settings.api_base_url}/api/tasks/import",
                headers=headers,
                files=files,
                timeout=settings.api_timeout
            )
            
            if response.status_code >= 400:
                raise APIException(f"Upload failed: {response.json().get('error', 'Unknown error')}")
            
            return response.json()
                
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise


def create_task_keyboard(task: Dict) -> InlineKeyboardMarkup:
    """Create inline keyboard for task actions"""
    keyboard = [
        [
            InlineKeyboardButton("✏️ Modifier", callback_data=f"edit_task_{task['id']}"),
            InlineKeyboardButton("✅ Terminé", callback_data=f"complete_task_{task['id']}")
        ],
        [
            InlineKeyboardButton("📝 Note", callback_data=f"add_note_{task['id']}"),
            InlineKeyboardButton("🗑️ Supprimer", callback_data=f"delete_task_{task['id']}")
        ],
        [
            InlineKeyboardButton("🔙 Retour", callback_data="back_to_tasks")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_status_keyboard(task_id: str) -> InlineKeyboardMarkup:
    """Create keyboard for status selection"""
    statuses = [
        ("En Attente", "⏳"),
        ("En Cours", "🔄"),
        ("Terminé", "✅"),
        ("Annulé", "❌"),
        ("En Pause", "⏸️")
    ]
    
    keyboard = []
    for status, emoji in statuses:
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {status}",
                callback_data=f"set_status_{task_id}_{status.replace(' ', '_')}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Annuler", callback_data=f"view_task_{task_id}")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_priority_keyboard(task_id: str) -> InlineKeyboardMarkup:
    """Create keyboard for priority selection"""
    priorities = [
        ("Urgent", "🔴"),
        ("Élevé", "🟠"),
        ("Moyen", "🟡"),
        ("Faible", "🟢")
    ]
    
    keyboard = []
    for priority, emoji in priorities:
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {priority}",
                callback_data=f"set_priority_{task_id}_{priority}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Annuler", callback_data=f"view_task_{task_id}")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_category_keyboard(action_type: str = "filter") -> InlineKeyboardMarkup:
    """Create keyboard for category selection"""
    categories = [
        ("Installation", "🔧"),
        ("Réparation", "🛠️"),
        ("Développement", "💻"),
        ("Livraison", "🚚"),
        ("Commercial", "💼")
    ]
    
    keyboard = []
    for category, emoji in categories:
        callback_data = f"{action_type}_category_{category.replace(' ', '_')}"
        keyboard.append([
            InlineKeyboardButton(f"{emoji} {category}", callback_data=callback_data)
        ])
    
    if action_type == "filter":
        keyboard.append([
            InlineKeyboardButton("🏠 Toutes", callback_data="filter_category_all")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Retour", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)


async def authenticate_user(telegram_user: User) -> Optional[Dict]:
    """Authenticate user with Microsoft Graph"""
    try:
        # In a real implementation, this would handle OAuth flow
        # For now, we'll simulate authentication
        user_data = {
            'id': str(telegram_user.id),
            'telegram_id': telegram_user.id,
            'username': telegram_user.username,
            'first_name': telegram_user.first_name,
            'last_name': telegram_user.last_name,
            'email': f"{telegram_user.username}@techmac.ma",  # Simulated
            'access_token': 'simulated_token',  # In real app, get from OAuth
            'roles': ['user']
        }
        
        # Create session
        session_token = user_session.create_session(telegram_user.id, user_data)
        
        return user_data
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None


def is_user_authorized(telegram_user: User) -> bool:
    """Check if user is authorized to use the bot"""
    if not settings.allowed_users:
        return True  # Allow all users if no restrictions
    
    user_id = str(telegram_user.id)
    username = telegram_user.username
    
    return (user_id in settings.allowed_users or 
            username in settings.allowed_users or
            user_id in settings.admin_users or
            username in settings.admin_users)


def format_duration(seconds: int) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}j {hours}h" if hours else f"{days}j"


def generate_task_report(tasks: List[Dict]) -> str:
    """Generate a formatted task report"""
    if not tasks:
        return "📋 Aucune tâche trouvée."
    
    report = f"📋 **Rapport des Tâches** ({len(tasks)} tâches)\n\n"
    
    # Group by status
    status_groups = {}
    for task in tasks:
        status = task.get('status', 'N/A')
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(task)
    
    for status, status_tasks in status_groups.items():
        report += f"**{format_task_status(status)}** ({len(status_tasks)})\n"
        
        for task in status_tasks[:5]:  # Limit to 5 tasks per status
            report += f"• {task.get('po_number', 'N/A')} - {truncate_text(task.get('action_description', ''), 40)}\n"
        
        if len(status_tasks) > 5:
            report += f"  ... et {len(status_tasks) - 5} autres\n"
        
        report += "\n"
    
    return report


# Export commonly used functions and classes
__all__ = [
    'APIClient', 'UserSession', 'RateLimiter', 'TaskManager', 'AnalyticsManager',
    'NotificationManager', 'FileManager', 'APIException', 'AuthenticationError',
    'require_auth', 'require_admin', 'rate_limit', 'format_datetime', 'format_task_status',
    'format_task_priority', 'format_task_category', 'format_task_summary',
    'format_statistics', 'send_long_message', 'create_task_keyboard',
    'create_status_keyboard', 'create_priority_keyboard', 'create_category_keyboard',
    'authenticate_user', 'is_user_authorized', 'format_duration', 'generate_task_report',
    'api_client', 'user_session', 'rate_limiter', 'logger'
]