# ===================================================================
# telegram-bot/bot.py
# ===================================================================
import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from telegram.error import TelegramError

# Local imports
from config import settings, BotMessages, BotCommands
from handlers import (
    CommandHandlers, TaskHandlers, CallbackHandlers, 
    FileHandlers, MessageHandlers,
    TASK_PO, TASK_DESCRIPTION, TASK_CUSTOMER, TASK_REQUESTER,
    TASK_RESPONSIBLE, TASK_CATEGORY, TASK_PRIORITY, TASK_DEADLINE,
    TASK_NOTES, SEARCH_TERM, WAITING_FILE, WAITING_NOTE
)
from utils import logger, user_session, rate_limiter
from keyboards import BotKeyboards

# Configure logging
logger = logging.getLogger(__name__)


class TelegramBot:
    """Main Telegram bot class"""
    
    def __init__(self):
        self.application: Optional[Application] = None
        self.is_running = False
        self.start_time = datetime.now()
        
    async def setup_bot(self):
        """Setup bot application and handlers"""
        try:
            # Create application
            self.application = Application.builder().token(settings.bot_token).build()
            
            # Setup command handlers
            await self._setup_command_handlers()
            
            # Setup conversation handlers
            await self._setup_conversation_handlers()
            
            # Setup callback handlers
            await self._setup_callback_handlers()
            
            # Setup message handlers
            await self._setup_message_handlers()
            
            # Setup error handler
            self.application.add_error_handler(self._error_handler)
            
            # Set bot commands
            await self._set_bot_commands()
            
            logger.info("Bot setup completed successfully")
            
        except Exception as e:
            logger.error(f"Error setting up bot: {e}")
            raise
    
    async def _setup_command_handlers(self):
        """Setup command handlers"""
        commands = [
            ("start", CommandHandlers.start),
            ("help", CommandHandlers.help_command),
            ("tasks", CommandHandlers.tasks_command),
            ("search", CommandHandlers.search_command),
            ("stats", CommandHandlers.stats_command),
            ("overdue", CommandHandlers.overdue_command),
            ("settings", CommandHandlers.settings_command),
            ("notifications", CommandHandlers.notifications_command),
            ("admin", CommandHandlers.admin_command),
            ("about", CommandHandlers.about_command),
            ("contact", CommandHandlers.contact_command),
        ]
        
        for command, handler in commands:
            self.application.add_handler(CommandHandler(command, handler))
            logger.debug(f"Added command handler: /{command}")
    
    async def _setup_conversation_handlers(self):
        """Setup conversation handlers for multi-step interactions"""
        
        # Task creation conversation
        task_creation_handler = ConversationHandler(
            entry_points=[CommandHandler("create", CommandHandlers.create_command)],
            states={
                TASK_PO: [MessageHandler(filters.TEXT & ~filters.COMMAND, TaskHandlers.handle_task_creation_po)],
                TASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, TaskHandlers.handle_task_creation_description)],
                TASK_CUSTOMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, TaskHandlers.handle_task_creation_customer)],
                TASK_REQUESTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, TaskHandlers.handle_task_creation_requester)],
                TASK_RESPONSIBLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, TaskHandlers.handle_task_creation_responsible)],
                TASK_CATEGORY: [CallbackQueryHandler(CallbackHandlers.handle_callback_query, pattern="^create_category_")],
                TASK_PRIORITY: [CallbackQueryHandler(CallbackHandlers.handle_callback_query, pattern="^create_priority_")],
                TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, TaskHandlers.handle_task_creation_deadline)],
                TASK_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, TaskHandlers.handle_task_creation_notes)],
            },
            fallbacks=[
                CommandHandler("cancel", TaskHandlers.cancel_task_creation),
                CallbackQueryHandler(CallbackHandlers.handle_callback_query, pattern="^cancel_task_creation$")
            ],
            conversation_timeout=600,  # 10 minutes timeout
        )
        
        self.application.add_handler(task_creation_handler)
        logger.debug("Added task creation conversation handler")
        
        # Search conversation
        search_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(CallbackHandlers.handle_callback_query, pattern="^free_search$"),
                MessageHandler(filters.Regex("^🔍 Rechercher$"), CommandHandlers.search_command)
            ],
            states={
                SEARCH_TERM: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_search_input)],
            },
            fallbacks=[CommandHandler("cancel", self._cancel_search)],
            conversation_timeout=300,  # 5 minutes timeout
        )
        
        self.application.add_handler(search_handler)
        logger.debug("Added search conversation handler")
    
    async def _setup_callback_handlers(self):
        """Setup callback query handlers"""
        self.application.add_handler(
            CallbackQueryHandler(CallbackHandlers.handle_callback_query)
        )
        logger.debug("Added callback query handler")
    
    async def _setup_message_handlers(self):
        """Setup message handlers"""
        
        # File handlers
        self.application.add_handler(
            MessageHandler(filters.Document.ALL, FileHandlers.handle_document)
        )
        
        # Photo handlers (for screenshots, etc.)
        self.application.add_handler(
            MessageHandler(filters.PHOTO, self._handle_photo)
        )
        
        # Contact and location handlers
        self.application.add_handler(
            MessageHandler(filters.CONTACT, self._handle_contact)
        )
        
        self.application.add_handler(
            MessageHandler(filters.LOCATION, self._handle_location)
        )
        
        # Text message handler (must be last)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, MessageHandlers.handle_text_message)
        )
        
        logger.debug("Added message handlers")
    
    async def _set_bot_commands(self):
        """Set bot commands for the menu"""
        try:
            commands = []
            
            # Public commands
            for command, description in BotCommands.COMMANDS:
                commands.append(BotCommand(command, description))
            
            await self.application.bot.set_my_commands(commands)
            logger.info(f"Set {len(commands)} bot commands")
            
        except Exception as e:
            logger.error(f"Error setting bot commands: {e}")
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Global error handler"""
        try:
            logger.error(f"Update {update} caused error {context.error}")
            
            # Get error details
            error_message = str(context.error)
            
            # Send user-friendly error message
            if update and update.effective_message:
                try:
                    if "Unauthorized" in error_message:
                        await update.effective_message.reply_text(
                            "🔐 Session expirée. Utilisez /start pour vous reconnecter."
                        )
                    elif "Bad Request" in error_message:
                        await update.effective_message.reply_text(
                            "❌ Requête invalide. Veuillez réessayer."
                        )
                    elif "Timeout" in error_message:
                        await update.effective_message.reply_text(
                            "⏱️ Délai d'attente dépassé. Veuillez réessayer."
                        )
                    else:
                        await update.effective_message.reply_text(
                            BotMessages.ERROR_GENERIC
                        )
                except Exception as send_error:
                    logger.error(f"Error sending error message: {send_error}")
            
            # Log additional context for debugging
            if update:
                logger.error(f"Update data: {update.to_dict()}")
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
    
    async def _handle_search_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle search term input"""
        search_term = update.message.text.strip()
        
        if len(search_term) < 2:
            await update.message.reply_text(
                "🔍 Veuillez entrer au moins 2 caractères pour la recherche."
            )
            return SEARCH_TERM
        
        await TaskHandlers.perform_search(update, context, search_term)
        return ConversationHandler.END
    
    async def _cancel_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel search conversation"""
        await update.message.reply_text(
            "❌ Recherche annulée.",
            reply_markup=BotKeyboards.main_menu()
        )
        return ConversationHandler.END
    
    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo uploads"""
        await update.message.reply_text(
            "📸 Photo reçue. Cette fonctionnalité sera bientôt disponible.",
            reply_markup=BotKeyboards.main_menu()
        )
    
    async def _handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle contact sharing"""
        contact = update.message.contact
        
        message = f"📞 **Contact reçu**\n\n"
        message += f"👤 Nom: {contact.first_name}"
        
        if contact.last_name:
            message += f" {contact.last_name}"
        
        message += f"\n📱 Téléphone: {contact.phone_number}"
        
        if contact.user_id:
            message += f"\n🆔 ID: {contact.user_id}"
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.main_menu()
        )
    
    async def _handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle location sharing"""
        location = update.message.location
        
        message = f"📍 **Position reçue**\n\n"
        message += f"🌍 Latitude: {location.latitude:.6f}\n"
        message += f"🌍 Longitude: {location.longitude:.6f}"
        
        if location.live_period:
            message += f"\n⏱️ Position en direct: {location.live_period}s"
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.main_menu()
        )
    
    async def start_polling(self):
        """Start bot with polling"""
        try:
            logger.info("Starting bot with polling...")
            self.is_running = True
            
            # Initialize bot
            await self.application.initialize()
            await self.application.start()
            
            # Start polling
            await self.application.updater.start_polling(
                poll_interval=1.0,
                timeout=10,
                bootstrap_retries=-1,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30,
                pool_timeout=30
            )
            
            logger.info("Bot started successfully with polling")
            
            # Keep running until stopped
            await self._run_until_stopped()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
        finally:
            await self.stop()
    
    async def start_webhook(self):
        """Start bot with webhook"""
        try:
            if not settings.webhook_url:
                raise ValueError("Webhook URL not configured")
            
            logger.info(f"Starting bot with webhook: {settings.webhook_url}")
            self.is_running = True
            
            # Initialize bot
            await self.application.initialize()
            await self.application.start()
            
            # Start webhook
            await self.application.updater.start_webhook(
                listen="0.0.0.0",
                port=settings.webhook_port,
                url_path=settings.webhook_secret,
                webhook_url=f"{settings.webhook_url}/{settings.webhook_secret}",
                bootstrap_retries=-1
            )
            
            logger.info("Bot started successfully with webhook")
            
            # Keep running until stopped
            await self._run_until_stopped()
            
        except Exception as e:
            logger.error(f"Error starting webhook: {e}")
            raise
        finally:
            await self.stop()
    
    async def _run_until_stopped(self):
        """Keep the bot running until stopped"""
        try:
            # Setup signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, shutting down...")
                asyncio.create_task(self.stop())
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Run until stopped
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
    
    async def stop(self):
        """Stop the bot gracefully"""
        try:
            logger.info("Stopping bot...")
            self.is_running = False
            
            if self.application:
                # Stop updater
                if self.application.updater.running:
                    await self.application.updater.stop()
                
                # Stop application
                await self.application.stop()
                await self.application.shutdown()
            
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    def get_stats(self) -> Dict:
        """Get bot statistics"""
        uptime = datetime.now() - self.start_time
        
        return {
            'uptime': str(uptime),
            'start_time': self.start_time.isoformat(),
            'is_running': self.is_running,
            'active_sessions': len(user_session.sessions),
            'rate_limited_users': len(rate_limiter.user_requests),
        }


# Background tasks and schedulers
class BotScheduler:
    """Background task scheduler for the bot"""
    
    def __init__(self, bot: TelegramBot):
        self.bot = bot
        self.tasks: List[asyncio.Task] = []
    
    async def start_background_tasks(self):
        """Start background tasks"""
        logger.info("Starting background tasks...")
        
        # Session cleanup task
        self.tasks.append(
            asyncio.create_task(self._session_cleanup_task())
        )
        
        # Notification check task
        if settings.enable_notifications:
            self.tasks.append(
                asyncio.create_task(self._notification_check_task())
            )
        
        # Health check task
        self.tasks.append(
            asyncio.create_task(self._health_check_task())
        )
        
        logger.info(f"Started {len(self.tasks)} background tasks")
    
    async def stop_background_tasks(self):
        """Stop all background tasks"""
        logger.info("Stopping background tasks...")
        
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.tasks.clear()
        logger.info("Background tasks stopped")
    
    async def _session_cleanup_task(self):
        """Clean up expired sessions periodically"""
        while True:
            try:
                # Clean up expired sessions
                expired_sessions = []
                current_time = datetime.now()
                
                for user_id, session in user_session.sessions.items():
                    if (current_time - session['last_activity']).total_seconds() > settings.session_timeout:
                        expired_sessions.append(user_id)
                
                for user_id in expired_sessions:
                    user_session.delete_session(user_id)
                
                if expired_sessions:
                    logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
                # Sleep for 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in session cleanup task: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute
    
    async def _notification_check_task(self):
        """Check for new notifications and send to users"""
        while True:
            try:
                # This would integrate with your notification system
                # For now, it's a placeholder
                await asyncio.sleep(settings.notification_check_interval)
                
            except Exception as e:
                logger.error(f"Error in notification check task: {e}")
                await asyncio.sleep(60)
    
    async def _health_check_task(self):
        """Periodic health check"""
        while True:
            try:
                # Check bot health
                if self.bot.application and self.bot.application.bot:
                    # Test bot connection
                    me = await self.bot.application.bot.get_me()
                    logger.debug(f"Health check OK - Bot: @{me.username}")
                
                # Sleep for 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                await asyncio.sleep(60)


# Main application entry point
async def main():
    """Main application entry point"""
    try:
        logger.info("Starting Action Plan Telegram Bot...")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Debug mode: {settings.debug}")
        
        # Create and setup bot
        bot = TelegramBot()
        await bot.setup_bot()
        
        # Create scheduler
        scheduler = BotScheduler(bot)
        
        try:
            # Start background tasks
            await scheduler.start_background_tasks()
            
            # Start bot (webhook or polling based on configuration)
            if settings.webhook_url:
                await bot.start_webhook()
            else:
                await bot.start_polling()
                
        finally:
            # Stop background tasks
            await scheduler.stop_background_tasks()
    
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        # Check required configuration
        if not settings.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            sys.exit(1)
        
        if not settings.api_base_url:
            logger.error("API_BASE_URL not set")
            sys.exit(1)
        
        # Run the bot
        asyncio.run(main())
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)