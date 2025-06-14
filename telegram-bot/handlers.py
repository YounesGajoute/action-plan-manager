# ===================================================================
# telegram-bot/handlers.py
# ===================================================================
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from telegram import Update, Message, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from telegram.error import TelegramError

from config import settings, BotMessages, BotCommands
from utils import (
    require_auth, require_admin, rate_limit, APIException, AuthenticationError,
    TaskManager, AnalyticsManager, NotificationManager, FileManager,
    format_task_summary, format_statistics, format_datetime,
    send_long_message, authenticate_user, is_user_authorized,
    user_session, logger
)
from keyboards import BotKeyboards

# Conversation states
(
    TASK_PO, TASK_DESCRIPTION, TASK_CUSTOMER, TASK_REQUESTER,
    TASK_RESPONSIBLE, TASK_CATEGORY, TASK_PRIORITY, TASK_DEADLINE,
    TASK_NOTES, SEARCH_TERM, WAITING_FILE, WAITING_NOTE
) = range(12)


class CommandHandlers:
    """Main command handlers for the bot"""
    
    @staticmethod
    @rate_limit
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        if not is_user_authorized(user):
            await update.message.reply_text(
                "🚫 Désolé, vous n'êtes pas autorisé à utiliser ce bot.\n"
                "Contactez votre administrateur pour obtenir l'accès."
            )
            return
        
        # Authenticate user
        user_data = await authenticate_user(user)
        
        if not user_data:
            await update.message.reply_text(
                "❌ Erreur d'authentification. Veuillez réessayer plus tard."
            )
            return
        
        # Send welcome message
        welcome_message = BotMessages.WELCOME.format(
            name=user.first_name or user.username or "Utilisateur"
        )
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.main_menu()
        )
        
        logger.info(f"User {user.id} ({user.username}) started the bot")
    
    @staticmethod
    @rate_limit
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(
            BotMessages.HELP,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.help_menu()
        )
    
    @staticmethod
    @require_auth
    @rate_limit
    async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tasks command"""
        try:
            user_id = update.effective_user.id
            
            # Get user tasks
            tasks = await TaskManager.get_user_tasks(user_id)
            
            if not tasks:
                await update.message.reply_text(
                    "📋 Vous n'avez aucune tâche pour le moment.\n"
                    "Utilisez /create pour créer une nouvelle tâche.",
                    reply_markup=BotKeyboards.main_menu()
                )
                return
            
            # Show tasks with pagination
            keyboard = BotKeyboards.task_list(tasks, page=0)
            
            message = f"📋 **Vos Tâches** ({len(tasks)} au total)\n\n"
            message += "Sélectionnez une tâche pour voir les détails :"
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
            
        except APIException as e:
            await update.message.reply_text(f"❌ Erreur API: {str(e)}")
        except Exception as e:
            logger.error(f"Error in tasks command: {e}")
            await update.message.reply_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    @require_auth
    @rate_limit
    async def create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /create command - start task creation"""
        await update.message.reply_text(
            "➕ **Création d'une nouvelle tâche**\n\n"
            "Commençons par le numéro de commande (PO).\n"
            "Entrez le numéro PO ou 'skip' pour passer :",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.remove_keyboard()
        )
        
        # Initialize task data in context
        context.user_data['new_task'] = {}
        
        return TASK_PO
    
    @staticmethod
    @require_auth
    @rate_limit
    async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        if context.args:
            # Search term provided in command
            search_term = ' '.join(context.args)
            await TaskHandlers.perform_search(update, context, search_term)
        else:
            # Show search options
            await update.message.reply_text(
                "🔍 **Recherche de Tâches**\n\n"
                "Choisissez votre méthode de recherche :",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=BotKeyboards.search_filters()
            )
    
    @staticmethod
    @require_auth
    @rate_limit
    async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        try:
            user_id = update.effective_user.id
            
            # Get dashboard statistics
            stats = await AnalyticsManager.get_dashboard_stats(user_id)
            
            if not stats:
                await update.message.reply_text(
                    "📊 Aucune statistique disponible pour le moment."
                )
                return
            
            # Format and send statistics
            stats_message = format_statistics(stats)
            
            await update.message.reply_text(
                stats_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=BotKeyboards.analytics_menu()
            )
            
        except APIException as e:
            await update.message.reply_text(f"❌ Erreur API: {str(e)}")
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await update.message.reply_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    @require_auth
    @rate_limit
    async def overdue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /overdue command"""
        try:
            user_id = update.effective_user.id
            
            # Get overdue tasks
            overdue_tasks = await TaskManager.get_overdue_tasks(user_id)
            
            if not overdue_tasks:
                await update.message.reply_text(
                    "✅ Parfait ! Vous n'avez aucune tâche en retard.",
                    reply_markup=BotKeyboards.main_menu()
                )
                return
            
            # Format overdue tasks message
            message = f"🔴 **Tâches en Retard** ({len(overdue_tasks)})\n\n"
            
            for task in overdue_tasks[:10]:  # Limit to 10 tasks
                deadline = format_datetime(task.get('deadline'))
                message += f"🔴 **{task.get('po_number', 'N/A')}**\n"
                message += f"📝 {task.get('action_description', 'N/A')[:50]}...\n"
                message += f"📅 Échéance: {deadline}\n"
                message += f"👤 {task.get('responsible', 'N/A')}\n\n"
            
            if len(overdue_tasks) > 10:
                message += f"... et {len(overdue_tasks) - 10} autres tâches en retard."
            
            await send_long_message(
                update,
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=BotKeyboards.task_list(overdue_tasks)
            )
            
        except APIException as e:
            await update.message.reply_text(f"❌ Erreur API: {str(e)}")
        except Exception as e:
            logger.error(f"Error in overdue command: {e}")
            await update.message.reply_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    @require_auth
    @rate_limit
    async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        await update.message.reply_text(
            "⚙️ **Paramètres**\n\n"
            "Configurez vos préférences :",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.settings_menu_inline()
        )
    
    @staticmethod
    @require_auth
    @rate_limit
    async def notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /notifications command"""
        try:
            user_id = update.effective_user.id
            
            # Get user notifications
            notifications = await NotificationManager.get_user_notifications(user_id)
            
            if not notifications:
                await update.message.reply_text(
                    "🔔 Aucune notification pour le moment.",
                    reply_markup=BotKeyboards.main_menu()
                )
                return
            
            # Format notifications
            message = f"🔔 **Notifications** ({len(notifications)})\n\n"
            
            for notif in notifications[:5]:  # Show recent 5
                emoji = "🔴" if not notif.get('read') else "⚪"
                message += f"{emoji} **{notif.get('title')}**\n"
                message += f"📝 {notif.get('message')}\n"
                message += f"📅 {format_datetime(notif.get('created_at'))}\n\n"
            
            if len(notifications) > 5:
                message += f"... et {len(notifications) - 5} autres notifications."
            
            await send_long_message(
                update,
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=BotKeyboards.notification_settings()
            )
            
        except APIException as e:
            await update.message.reply_text(f"❌ Erreur API: {str(e)}")
        except Exception as e:
            logger.error(f"Error in notifications command: {e}")
            await update.message.reply_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    @require_admin
    @rate_limit
    async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command"""
        await update.message.reply_text(
            "👨‍💼 **Panneau d'Administration**\n\n"
            "Choisissez une action :",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.admin_menu()
        )
    
    @staticmethod
    @rate_limit
    async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /about command"""
        about_message = (
            "ℹ️ **Action Plan Management System**\n\n"
            f"🤖 **Version:** {settings.version if hasattr(settings, 'version') else '1.0.0'}\n"
            f"🏢 **Entreprise:** TechMac\n"
            f"📅 **Dernière mise à jour:** {datetime.now().strftime('%d/%m/%Y')}\n\n"
            "📝 **Description:**\n"
            "Ce bot vous permet de gérer vos plans d'action et tâches "
            "directement depuis Telegram avec synchronisation Microsoft 365.\n\n"
            "🛠️ **Fonctionnalités:**\n"
            "• Gestion des tâches\n"
            "• Statistiques et rapports\n"
            "• Notifications en temps réel\n"
            "• Synchronisation OneDrive\n"
            "• Interface intuitive\n\n"
            "📞 **Support:** /contact"
        )
        
        await update.message.reply_text(
            about_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.help_menu()
        )
    
    @staticmethod
    @rate_limit
    async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /contact command"""
        contact_message = (
            "📞 **Contact & Support**\n\n"
            "🏢 **TechMac Support**\n"
            "📧 Email: support@techmac.ma\n"
            "📱 Téléphone: +212 XXX-XXXXXX\n"
            "🌐 Web: www.techmac.ma\n\n"
            "⏰ **Heures d'ouverture:**\n"
            "Lundi - Vendredi: 08h00 - 18h00\n"
            "Samedi: 09h00 - 13h00\n\n"
            "🚨 **Urgences:**\n"
            "Pour les urgences techniques, contactez le support par téléphone."
        )
        
        await update.message.reply_text(
            contact_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.contact_keyboard()
        )


class TaskHandlers:
    """Task-related handlers"""
    
    @staticmethod
    async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE, search_term: str):
        """Perform task search"""
        try:
            user_id = update.effective_user.id
            
            # Perform search
            tasks = await TaskManager.search_tasks(user_id, search_term)
            
            if not tasks:
                await update.message.reply_text(
                    f"🔍 Aucune tâche trouvée pour '{search_term}'.\n"
                    "Essayez avec d'autres mots-clés.",
                    reply_markup=BotKeyboards.search_filters()
                )
                return
            
            # Show results
            message = f"🔍 **Résultats de recherche pour '{search_term}'**\n"
            message += f"📊 {len(tasks)} tâche(s) trouvée(s)\n\n"
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=BotKeyboards.task_list(tasks)
            )
            
        except APIException as e:
            await update.message.reply_text(f"❌ Erreur de recherche: {str(e)}")
        except Exception as e:
            logger.error(f"Error in search: {e}")
            await update.message.reply_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    async def handle_task_creation_po(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle PO number input in task creation"""
        po_number = update.message.text.strip()
        
        if po_number.lower() != 'skip':
            context.user_data['new_task']['po_number'] = po_number
        
        await update.message.reply_text(
            "📝 **Description de l'action**\n\n"
            "Décrivez l'action à réaliser :"
        )
        
        return TASK_DESCRIPTION
    
    @staticmethod
    async def handle_task_creation_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle description input in task creation"""
        description = update.message.text.strip()
        context.user_data['new_task']['action_description'] = description
        
        await update.message.reply_text(
            "🏢 **Client**\n\n"
            "Nom du client :"
        )
        
        return TASK_CUSTOMER
    
    @staticmethod
    async def handle_task_creation_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle customer input in task creation"""
        customer = update.message.text.strip()
        context.user_data['new_task']['customer'] = customer
        
        await update.message.reply_text(
            "👤 **Demandeur**\n\n"
            "Nom de la personne qui a fait la demande :"
        )
        
        return TASK_REQUESTER
    
    @staticmethod
    async def handle_task_creation_requester(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle requester input in task creation"""
        requester = update.message.text.strip()
        context.user_data['new_task']['requester'] = requester
        
        await update.message.reply_text(
            "👷 **Responsable TechMac**\n\n"
            "Nom du responsable de la tâche :"
        )
        
        return TASK_RESPONSIBLE
    
    @staticmethod
    async def handle_task_creation_responsible(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle responsible input in task creation"""
        responsible = update.message.text.strip()
        context.user_data['new_task']['responsible'] = responsible
        
        await update.message.reply_text(
            "🏷️ **Catégorie**\n\n"
            "Choisissez la catégorie de la tâche :",
            reply_markup=BotKeyboards.task_category_selector("create")
        )
        
        return TASK_CATEGORY
    
    @staticmethod
    async def handle_task_creation_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category selection in task creation"""
        # This will be handled by callback query
        return TASK_PRIORITY
    
    @staticmethod
    async def handle_task_creation_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle priority selection in task creation"""
        # This will be handled by callback query
        return TASK_DEADLINE
    
    @staticmethod
    async def handle_task_creation_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle deadline input in task creation"""
        deadline_text = update.message.text.strip()
        
        if deadline_text.lower() not in ['skip', 'passer']:
            # Try to parse date (simplified - in production use proper date parsing)
            try:
                # Expected format: DD/MM/YYYY or DD/MM/YY
                from datetime import datetime
                if '/' in deadline_text:
                    parts = deadline_text.split('/')
                    if len(parts) == 3:
                        day, month, year = parts
                        if len(year) == 2:
                            year = '20' + year
                        deadline = datetime(int(year), int(month), int(day))
                        context.user_data['new_task']['deadline'] = deadline.isoformat()
            except ValueError:
                await update.message.reply_text(
                    "❌ Format de date invalide. Utilisez DD/MM/YYYY ou 'skip' pour passer."
                )
                return TASK_DEADLINE
        
        await update.message.reply_text(
            "📝 **Notes (optionnel)**\n\n"
            "Ajoutez des notes ou commentaires, ou tapez 'skip' pour terminer :"
        )
        
        return TASK_NOTES
    
    @staticmethod
    async def handle_task_creation_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle notes input and complete task creation"""
        notes = update.message.text.strip()
        
        if notes.lower() != 'skip':
            context.user_data['new_task']['notes'] = notes
        
        # Show task summary for confirmation
        task_data = context.user_data.get('new_task', {})
        
        summary = "✅ **Résumé de la nouvelle tâche**\n\n"
        summary += f"📋 **PO:** {task_data.get('po_number', 'N/A')}\n"
        summary += f"📝 **Action:** {task_data.get('action_description', 'N/A')}\n"
        summary += f"🏢 **Client:** {task_data.get('customer', 'N/A')}\n"
        summary += f"👤 **Demandeur:** {task_data.get('requester', 'N/A')}\n"
        summary += f"👷 **Responsable:** {task_data.get('responsible', 'N/A')}\n"
        
        if task_data.get('category'):
            summary += f"🏷️ **Catégorie:** {task_data['category']}\n"
        
        if task_data.get('priority'):
            summary += f"⚡ **Priorité:** {task_data['priority']}\n"
        
        if task_data.get('deadline'):
            deadline = format_datetime(task_data['deadline'])
            summary += f"📅 **Échéance:** {deadline}\n"
        
        if task_data.get('notes'):
            summary += f"📝 **Notes:** {task_data['notes']}\n"
        
        await update.message.reply_text(
            summary,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.yes_no("confirm_create_task")
        )
        
        return ConversationHandler.END
    
    @staticmethod
    async def cancel_task_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel task creation"""
        context.user_data.pop('new_task', None)
        
        await update.message.reply_text(
            "❌ Création de tâche annulée.",
            reply_markup=BotKeyboards.main_menu()
        )
        
        return ConversationHandler.END


class CallbackHandlers:
    """Callback query handlers for inline keyboards"""
    
    @staticmethod
    async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main callback query handler"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        try:
            # Route callback to appropriate handler
            if data == "main_menu":
                await CallbackHandlers.show_main_menu(query, context)
            
            elif data.startswith("view_task_"):
                task_id = data.split("_", 2)[2]
                await CallbackHandlers.show_task_details(query, context, task_id)
            
            elif data.startswith("edit_task_"):
                task_id = data.split("_", 2)[2]
                await CallbackHandlers.edit_task(query, context, task_id)
            
            elif data.startswith("complete_task_"):
                task_id = data.split("_", 2)[2]
                await CallbackHandlers.complete_task(query, context, task_id)
            
            elif data.startswith("delete_task_"):
                task_id = data.split("_", 2)[2]
                await CallbackHandlers.delete_task_confirm(query, context, task_id)
            
            elif data.startswith("confirm_delete_task_"):
                task_id = data.split("_", 3)[3]
                await CallbackHandlers.delete_task(query, context, task_id)
            
            elif data.startswith("set_status_"):
                parts = data.split("_", 3)
                task_id, status = parts[2], parts[3].replace("_", " ")
                await CallbackHandlers.update_task_status(query, context, task_id, status)
            
            elif data.startswith("set_priority_"):
                parts = data.split("_", 3)
                task_id, priority = parts[2], parts[3]
                await CallbackHandlers.update_task_priority(query, context, task_id, priority)
            
            elif data.startswith("create_category_"):
                category = data.split("_", 2)[2].replace("_", " ")
                if category == "none":
                    category = None
                await CallbackHandlers.set_task_category(query, context, category)
            
            elif data.startswith("tasks_page_"):
                page = int(data.split("_", 2)[2])
                await CallbackHandlers.show_tasks_page(query, context, page)
            
            elif data.startswith("filter_"):
                await CallbackHandlers.handle_filter(query, context, data)
            
            elif data == "show_dashboard":
                await CallbackHandlers.show_dashboard(query, context)
            
            elif data == "analytics_menu":
                await CallbackHandlers.show_analytics_menu(query, context)
            
            elif data == "settings_menu":
                await CallbackHandlers.show_settings_menu(query, context)
            
            elif data.startswith("confirm_create_task"):
                await CallbackHandlers.confirm_create_task(query, context)
            
            else:
                await query.edit_message_text("❓ Action non reconnue.")
                
        except APIException as e:
            await query.edit_message_text(f"❌ Erreur API: {str(e)}")
        except Exception as e:
            logger.error(f"Error in callback handler: {e}")
            await query.edit_message_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    async def show_main_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu"""
        await query.edit_message_text(
            "🏠 **Menu Principal**\n\n"
            "Que souhaitez-vous faire ?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.quick_actions()
        )
    
    @staticmethod
    async def show_task_details(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, task_id: str):
        """Show detailed task information"""
        try:
            user_id = query.from_user.id
            task = await TaskManager.get_task_details(user_id, task_id)
            
            if not task:
                await query.edit_message_text("❌ Tâche non trouvée.")
                return
            
            # Format task details
            details = format_task_summary(task)
            
            await query.edit_message_text(
                details,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=BotKeyboards.task_detail(task)
            )
            
        except Exception as e:
            logger.error(f"Error showing task details: {e}")
            await query.edit_message_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    async def complete_task(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, task_id: str):
        """Mark task as completed"""
        try:
            user_id = query.from_user.id
            
            # Update task status
            updates = {'status': 'Terminé'}
            await TaskManager.update_task(user_id, task_id, updates)
            
            await query.edit_message_text(
                "✅ Tâche marquée comme terminée !",
                reply_markup=BotKeyboards.main_menu()
            )
            
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            await query.edit_message_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    async def delete_task_confirm(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, task_id: str):
        """Show delete confirmation"""
        await query.edit_message_text(
            "🗑️ **Supprimer la tâche**\n\n"
            "⚠️ Cette action est irréversible.\n"
            "Êtes-vous sûr de vouloir supprimer cette tâche ?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.confirmation_dialog("delete_task", task_id)
        )
    
    @staticmethod
    async def delete_task(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, task_id: str):
        """Delete task"""
        try:
            user_id = query.from_user.id
            
            # Delete task
            await TaskManager.delete_task(user_id, task_id)
            
            await query.edit_message_text(
                "🗑️ Tâche supprimée avec succès !",
                reply_markup=BotKeyboards.main_menu()
            )
            
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            await query.edit_message_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    async def update_task_status(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, task_id: str, status: str):
        """Update task status"""
        try:
            user_id = query.from_user.id
            
            # Update task
            updates = {'status': status}
            await TaskManager.update_task(user_id, task_id, updates)
            
            await query.edit_message_text(
                f"✅ Statut mis à jour : {status}",
                reply_markup=BotKeyboards.main_menu()
            )
            
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            await query.edit_message_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    async def update_task_priority(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, task_id: str, priority: str):
        """Update task priority"""
        try:
            user_id = query.from_user.id
            
            # Update task
            updates = {'priority': priority}
            await TaskManager.update_task(user_id, task_id, updates)
            
            await query.edit_message_text(
                f"⚡ Priorité mise à jour : {priority}",
                reply_markup=BotKeyboards.main_menu()
            )
            
        except Exception as e:
            logger.error(f"Error updating task priority: {e}")
            await query.edit_message_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    async def set_task_category(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, category: Optional[str]):
        """Set task category during creation"""
        if 'new_task' not in context.user_data:
            await query.edit_message_text("❌ Session de création expirée.")
            return
        
        if category:
            context.user_data['new_task']['category'] = category
        
        await query.edit_message_text(
            "⚡ **Priorité**\n\n"
            "Choisissez la priorité de la tâche :",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.task_priority_selector("create")
        )
    
    @staticmethod
    async def show_tasks_page(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, page: int):
        """Show tasks with pagination"""
        try:
            user_id = query.from_user.id
            tasks = await TaskManager.get_user_tasks(user_id)
            
            message = f"📋 **Vos Tâches** ({len(tasks)} au total)\n\n"
            message += "Sélectionnez une tâche pour voir les détails :"
            
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=BotKeyboards.task_list(tasks, page=page)
            )
            
        except Exception as e:
            logger.error(f"Error showing tasks page: {e}")
            await query.edit_message_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    async def show_dashboard(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """Show dashboard statistics"""
        try:
            user_id = query.from_user.id
            stats = await AnalyticsManager.get_dashboard_stats(user_id)
            
            if not stats:
                await query.edit_message_text("📊 Aucune statistique disponible.")
                return
            
            stats_message = format_statistics(stats)
            
            await query.edit_message_text(
                stats_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=BotKeyboards.analytics_menu()
            )
            
        except Exception as e:
            logger.error(f"Error showing dashboard: {e}")
            await query.edit_message_text(BotMessages.ERROR_GENERIC)
    
    @staticmethod
    async def show_analytics_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """Show analytics menu"""
        await query.edit_message_text(
            "📊 **Analyses et Rapports**\n\n"
            "Choisissez le type d'analyse :",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.analytics_menu()
        )
    
    @staticmethod
    async def show_settings_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu"""
        await query.edit_message_text(
            "⚙️ **Paramètres**\n\n"
            "Configurez vos préférences :",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BotKeyboards.settings_menu_inline()
        )
    
    @staticmethod
    async def confirm_create_task(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and create new task"""
        if query.data.endswith("_yes"):
            try:
                user_id = query.from_user.id
                task_data = context.user_data.get('new_task', {})
                
                # Create task
                new_task = await TaskManager.create_task(user_id, task_data)
                
                # Clear temporary data
                context.user_data.pop('new_task', None)
                
                await query.edit_message_text(
                    f"✅ **Tâche créée avec succès !**\n\n"
                    f"📋 ID: {new_task.get('id', 'N/A')}\n"
                    f"📝 Action: {task_data.get('action_description', 'N/A')}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=BotKeyboards.main_menu()
                )
                
            except Exception as e:
                logger.error(f"Error creating task: {e}")
                await query.edit_message_text(
                    "❌ Erreur lors de la création de la tâche.\n"
                    "Veuillez réessayer.",
                    reply_markup=BotKeyboards.main_menu()
                )
        else:
            # User cancelled
            context.user_data.pop('new_task', None)
            await query.edit_message_text(
                "❌ Création de tâche annulée.",
                reply_markup=BotKeyboards.main_menu()
            )
    
    @staticmethod
    async def handle_filter(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle filter callbacks"""
        try:
            user_id = query.from_user.id
            
            if data == "filter_by_status":
                await query.edit_message_text(
                    "📊 **Filtrer par Statut**\n\n"
                    "Choisissez un statut :",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=BotKeyboards.status_filter()
                )
            
            elif data == "filter_by_category":
                await query.edit_message_text(
                    "🏷️ **Filtrer par Catégorie**\n\n"
                    "Choisissez une catégorie :",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=BotKeyboards.task_category_selector("filter")
                )
            
            elif data.startswith("filter_status_"):
                status = data.split("_", 2)[2].replace("_", " ")
                
                if status == "overdue":
                    tasks = await TaskManager.get_overdue_tasks(user_id)
                    filter_name = "en retard"
                else:
                    filters = {'status': status}
                    tasks = await TaskManager.get_user_tasks(user_id, filters)
                    filter_name = status
                
                if not tasks:
                    await query.edit_message_text(
                        f"📋 Aucune tâche {filter_name} trouvée.",
                        reply_markup=BotKeyboards.search_filters()
                    )
                    return
                
                message = f"📋 **Tâches {filter_name}** ({len(tasks)})\n\n"
                
                await query.edit_message_text(
                    message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=BotKeyboards.task_list(tasks)
                )
            
        except Exception as e:
            logger.error(f"Error handling filter: {e}")
            await query.edit_message_text(BotMessages.ERROR_GENERIC)


class FileHandlers:
    """File upload and processing handlers"""
    
    @staticmethod
    @require_auth
    async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads"""
        document = update.message.document
        
        if not document:
            return
        
        # Check file type
        if not document.file_name.lower().endswith(('.xlsx', '.xls')):
            await update.message.reply_text(
                "❌ Format de fichier non supporté.\n"
                "Veuillez envoyer un fichier Excel (.xlsx ou .xls)."
            )
            return
        
        # Check file size (max 10MB)
        if document.file_size > 10 * 1024 * 1024:
            await update.message.reply_text(
                "❌ Fichier trop volumineux (max 10MB)."
            )
            return
        
        try:
            # Download file
            file = await context.bot.get_file(document.file_id)
            file_data = await file.download_as_bytearray()
            
            # Show processing message
            processing_message = await update.message.reply_text(
                "⏳ Traitement du fichier Excel en cours..."
            )
            
            # Upload and process file
            user_id = update.effective_user.id
            result = await FileManager.upload_excel_file(
                user_id, 
                bytes(file_data), 
                document.file_name
            )
            
            # Format result message
            imported = result.get('imported', 0)
            errors = result.get('errors', [])
            
            result_message = f"✅ **Importation terminée !**\n\n"
            result_message += f"📊 **Résultats:**\n"
            result_message += f"• Tâches importées: {imported}\n"
            
            if errors:
                result_message += f"• Erreurs: {len(errors)}\n\n"
                result_message += "⚠️ **Erreurs détectées:**\n"
                for error in errors[:5]:  # Show first 5 errors
                    result_message += f"• {error}\n"
                
                if len(errors) > 5:
                    result_message += f"• ... et {len(errors) - 5} autres erreurs.\n"
            
            await processing_message.edit_text(
                result_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=BotKeyboards.main_menu()
            )
            
        except APIException as e:
            await processing_message.edit_text(f"❌ Erreur d'importation: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            await processing_message.edit_text(BotMessages.ERROR_GENERIC)


class MessageHandlers:
    """Text message handlers"""
    
    @staticmethod
    async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        text = update.message.text
        
        # Handle menu button presses
        if text == "📋 Mes Tâches":
            await CommandHandlers.tasks_command(update, context)
        
        elif text == "➕ Nouvelle Tâche":
            await CommandHandlers.create_command(update, context)
        
        elif text == "📊 Statistiques":
            await CommandHandlers.stats_command(update, context)
        
        elif text == "🔍 Rechercher":
            await CommandHandlers.search_command(update, context)
        
        elif text == "⚙️ Paramètres":
            await CommandHandlers.settings_command(update, context)
        
        elif text == "ℹ️ Aide":
            await CommandHandlers.help_command(update, context)
        
        elif text == "🏠 Menu Principal":
            await update.message.reply_text(
                "🏠 **Menu Principal**\n\n"
                "Choisissez une action :",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=BotKeyboards.main_menu()
            )
        
        else:
            # Unknown text, show help
            await update.message.reply_text(
                "❓ Commande non reconnue.\n"
                "Utilisez /help pour voir les commandes disponibles.",
                reply_markup=BotKeyboards.main_menu()
            )


# Export handlers
__all__ = [
    'CommandHandlers',
    'TaskHandlers', 
    'CallbackHandlers',
    'FileHandlers',
    'MessageHandlers',
    'TASK_PO', 'TASK_DESCRIPTION', 'TASK_CUSTOMER', 'TASK_REQUESTER',
    'TASK_RESPONSIBLE', 'TASK_CATEGORY', 'TASK_PRIORITY', 'TASK_DEADLINE',
    'TASK_NOTES', 'SEARCH_TERM', 'WAITING_FILE', 'WAITING_NOTE'
]