# ===================================================================
# telegram-bot/keyboards.py
# ===================================================================
from typing import List, Dict, Optional
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from config import KeyboardLayouts


class BotKeyboards:
    """Centralized keyboard management for the Telegram bot"""
    
    @staticmethod
    def main_menu() -> ReplyKeyboardMarkup:
        """Main menu keyboard"""
        return ReplyKeyboardMarkup(
            KeyboardLayouts.MAIN_MENU,
            resize_keyboard=True,
            one_time_keyboard=False
        )
    
    @staticmethod
    def task_actions() -> ReplyKeyboardMarkup:
        """Task actions keyboard"""
        return ReplyKeyboardMarkup(
            KeyboardLayouts.TASK_ACTIONS,
            resize_keyboard=True,
            one_time_keyboard=False
        )
    
    @staticmethod
    def settings_menu() -> ReplyKeyboardMarkup:
        """Settings menu keyboard"""
        return ReplyKeyboardMarkup(
            KeyboardLayouts.SETTINGS_MENU,
            resize_keyboard=True,
            one_time_keyboard=False
        )
    
    @staticmethod
    def yes_no(callback_prefix: str) -> InlineKeyboardMarkup:
        """Simple yes/no confirmation keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Oui", callback_data=f"{callback_prefix}_yes"),
                InlineKeyboardButton("❌ Non", callback_data=f"{callback_prefix}_no")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def task_list(tasks: List[Dict], page: int = 0, items_per_page: int = 5) -> InlineKeyboardMarkup:
        """Task list with pagination"""
        keyboard = []
        
        # Calculate pagination
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(tasks))
        page_tasks = tasks[start_idx:end_idx]
        
        # Task buttons
        for task in page_tasks:
            task_text = f"📋 {task.get('po_number', 'N/A')} - {task.get('customer', 'N/A')}"
            if len(task_text) > 35:
                task_text = task_text[:32] + "..."
            
            keyboard.append([
                InlineKeyboardButton(
                    task_text,
                    callback_data=f"view_task_{task['id']}"
                )
            ])
        
        # Pagination controls
        nav_buttons = []
        total_pages = (len(tasks) + items_per_page - 1) // items_per_page
        
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton("⬅️", callback_data=f"tasks_page_{page-1}")
            )
        
        if total_pages > 1:
            nav_buttons.append(
                InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop")
            )
        
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton("➡️", callback_data=f"tasks_page_{page+1}")
            )
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # Action buttons
        action_buttons = [
            InlineKeyboardButton("➕ Nouvelle", callback_data="create_task"),
            InlineKeyboardButton("🔍 Rechercher", callback_data="search_tasks")
        ]
        keyboard.append(action_buttons)
        
        # Back button
        keyboard.append([
            InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def task_detail(task: Dict) -> InlineKeyboardMarkup:
        """Task detail actions keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("✏️ Modifier", callback_data=f"edit_task_{task['id']}"),
                InlineKeyboardButton("📝 Note", callback_data=f"add_note_{task['id']}")
            ],
            [
                InlineKeyboardButton("📊 Statut", callback_data=f"change_status_{task['id']}"),
                InlineKeyboardButton("⚡ Priorité", callback_data=f"change_priority_{task['id']}")
            ]
        ]
        
        # Add complete/reopen button based on current status
        if task.get('status') == 'Terminé':
            keyboard.append([
                InlineKeyboardButton("🔄 Rouvrir", callback_data=f"reopen_task_{task['id']}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("✅ Marquer Terminé", callback_data=f"complete_task_{task['id']}")
            ])
        
        # Delete and back buttons
        keyboard.extend([
            [
                InlineKeyboardButton("🗑️ Supprimer", callback_data=f"delete_task_{task['id']}")
            ],
            [
                InlineKeyboardButton("🔙 Retour", callback_data="back_to_tasks")
            ]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def task_status_selector(task_id: str) -> InlineKeyboardMarkup:
        """Task status selection keyboard"""
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
            InlineKeyboardButton("🔙 Retour", callback_data=f"view_task_{task_id}")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def task_priority_selector(task_id: str) -> InlineKeyboardMarkup:
        """Task priority selection keyboard"""
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
            InlineKeyboardButton("🔙 Retour", callback_data=f"view_task_{task_id}")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def task_category_selector(context: str = "create") -> InlineKeyboardMarkup:
        """Task category selection keyboard"""
        categories = [
            ("Installation", "🔧"),
            ("Réparation", "🛠️"),
            ("Développement", "💻"),
            ("Livraison", "🚚"),
            ("Commercial", "💼")
        ]
        
        keyboard = []
        for category, emoji in categories:
            callback_data = f"{context}_category_{category.replace(' ', '_')}"
            keyboard.append([
                InlineKeyboardButton(f"{emoji} {category}", callback_data=callback_data)
            ])
        
        # Add "None" option for optional category
        if context == "create":
            keyboard.append([
                InlineKeyboardButton("❌ Aucune", callback_data="create_category_none")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Annuler", callback_data="cancel_task_creation")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def search_filters() -> InlineKeyboardMarkup:
        """Search and filter options keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Par Statut", callback_data="filter_by_status"),
                InlineKeyboardButton("🏷️ Par Catégorie", callback_data="filter_by_category")
            ],
            [
                InlineKeyboardButton("👤 Par Responsable", callback_data="filter_by_responsible"),
                InlineKeyboardButton("🏢 Par Client", callback_data="filter_by_customer")
            ],
            [
                InlineKeyboardButton("⚡ Par Priorité", callback_data="filter_by_priority"),
                InlineKeyboardButton("📅 Par Date", callback_data="filter_by_date")
            ],
            [
                InlineKeyboardButton("🔍 Recherche Libre", callback_data="free_search"),
                InlineKeyboardButton("🗂️ Toutes les Tâches", callback_data="show_all_tasks")
            ],
            [
                InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def status_filter() -> InlineKeyboardMarkup:
        """Status filter keyboard"""
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
                    callback_data=f"filter_status_{status.replace(' ', '_')}"
                )
            ])
        
        keyboard.extend([
            [
                InlineKeyboardButton("🔴 En Retard", callback_data="filter_status_overdue")
            ],
            [
                InlineKeyboardButton("🔙 Retour", callback_data="search_menu")
            ]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def priority_filter() -> InlineKeyboardMarkup:
        """Priority filter keyboard"""
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
                    callback_data=f"filter_priority_{priority}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Retour", callback_data="search_menu")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def analytics_menu() -> InlineKeyboardMarkup:
        """Analytics and reports menu"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Tableau de Bord", callback_data="show_dashboard"),
                InlineKeyboardButton("📈 Performance", callback_data="show_performance")
            ],
            [
                InlineKeyboardButton("🏷️ Par Catégorie", callback_data="stats_by_category"),
                InlineKeyboardButton("👤 Par Responsable", callback_data="stats_by_responsible")
            ],
            [
                InlineKeyboardButton("📅 Cette Semaine", callback_data="stats_weekly"),
                InlineKeyboardButton("📆 Ce Mois", callback_data="stats_monthly")
            ],
            [
                InlineKeyboardButton("📋 Rapport Détaillé", callback_data="generate_report"),
                InlineKeyboardButton("📊 Graphiques", callback_data="show_charts")
            ],
            [
                InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def settings_menu_inline() -> InlineKeyboardMarkup:
        """Settings menu (inline version)"""
        keyboard = [
            [
                InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications"),
                InlineKeyboardButton("🌐 Langue", callback_data="settings_language")
            ],
            [
                InlineKeyboardButton("⏰ Fuseau Horaire", callback_data="settings_timezone"),
                InlineKeyboardButton("📱 Préférences", callback_data="settings_preferences")
            ],
            [
                InlineKeyboardButton("🔐 Sécurité", callback_data="settings_security"),
                InlineKeyboardButton("📊 Affichage", callback_data="settings_display")
            ],
            [
                InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def notification_settings() -> InlineKeyboardMarkup:
        """Notification settings keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("🔔 Activer Tout", callback_data="notifications_enable_all"),
                InlineKeyboardButton("🔕 Désactiver Tout", callback_data="notifications_disable_all")
            ],
            [
                InlineKeyboardButton("📋 Nouvelles Tâches", callback_data="toggle_notif_new_tasks"),
                InlineKeyboardButton("✅ Tâches Terminées", callback_data="toggle_notif_completed")
            ],
            [
                InlineKeyboardButton("⏰ Échéances", callback_data="toggle_notif_deadlines"),
                InlineKeyboardButton("🔴 En Retard", callback_data="toggle_notif_overdue")
            ],
            [
                InlineKeyboardButton("📊 Rapports", callback_data="toggle_notif_reports"),
                InlineKeyboardButton("🔄 Mises à Jour", callback_data="toggle_notif_updates")
            ],
            [
                InlineKeyboardButton("🔙 Retour", callback_data="settings_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        """Admin menu keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("👥 Utilisateurs", callback_data="admin_users"),
                InlineKeyboardButton("📊 Statistiques", callback_data="admin_stats")
            ],
            [
                InlineKeyboardButton("📋 Toutes les Tâches", callback_data="admin_all_tasks"),
                InlineKeyboardButton("🔄 Synchronisation", callback_data="admin_sync")
            ],
            [
                InlineKeyboardButton("📝 Logs", callback_data="admin_logs"),
                InlineKeyboardButton("📢 Diffusion", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton("💾 Sauvegarde", callback_data="admin_backup"),
                InlineKeyboardButton("⚙️ Système", callback_data="admin_system")
            ],
            [
                InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def task_creation_steps(current_step: str) -> InlineKeyboardMarkup:
        """Task creation step navigation"""
        steps = [
            ("po", "📋 PO"),
            ("description", "📝 Description"),
            ("customer", "🏢 Client"),
            ("responsible", "👤 Responsable"),
            ("category", "🏷️ Catégorie"),
            ("priority", "⚡ Priorité"),
            ("deadline", "📅 Échéance"),
            ("confirm", "✅ Confirmer")
        ]
        
        keyboard = []
        current_index = next((i for i, (step, _) in enumerate(steps) if step == current_step), 0)
        
        # Progress indicator
        progress_text = f"Étape {current_index + 1}/{len(steps)}"
        keyboard.append([
            InlineKeyboardButton(progress_text, callback_data="noop")
        ])
        
        # Navigation buttons
        nav_buttons = []
        if current_index > 0:
            prev_step = steps[current_index - 1][0]
            nav_buttons.append(
                InlineKeyboardButton("⬅️ Précédent", callback_data=f"create_step_{prev_step}")
            )
        
        if current_index < len(steps) - 1:
            next_step = steps[current_index + 1][0]
            nav_buttons.append(
                InlineKeyboardButton("Suivant ➡️", callback_data=f"create_step_{next_step}")
            )
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # Action buttons
        action_buttons = [
            InlineKeyboardButton("💾 Sauvegarder", callback_data="save_task_draft"),
            InlineKeyboardButton("❌ Annuler", callback_data="cancel_task_creation")
        ]
        keyboard.append(action_buttons)
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def file_upload_options() -> InlineKeyboardMarkup:
        """File upload options keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Excel (.xlsx)", callback_data="upload_excel"),
                InlineKeyboardButton("📄 CSV", callback_data="upload_csv")
            ],
            [
                InlineKeyboardButton("📋 Modèle Excel", callback_data="download_template"),
                InlineKeyboardButton("❓ Aide Format", callback_data="format_help")
            ],
            [
                InlineKeyboardButton("🔙 Retour", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def export_options() -> InlineKeyboardMarkup:
        """Export options keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Excel", callback_data="export_excel"),
                InlineKeyboardButton("📄 CSV", callback_data="export_csv")
            ],
            [
                InlineKeyboardButton("📋 PDF", callback_data="export_pdf"),
                InlineKeyboardButton("📧 Email", callback_data="export_email")
            ],
            [
                InlineKeyboardButton("🔍 Filtres", callback_data="export_filters"),
                InlineKeyboardButton("📅 Période", callback_data="export_period")
            ],
            [
                InlineKeyboardButton("🔙 Retour", callback_data="analytics_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def time_period_selector(context: str = "stats") -> InlineKeyboardMarkup:
        """Time period selection keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("📅 Aujourd'hui", callback_data=f"{context}_period_today"),
                InlineKeyboardButton("📆 Cette Semaine", callback_data=f"{context}_period_week")
            ],
            [
                InlineKeyboardButton("📊 Ce Mois", callback_data=f"{context}_period_month"),
                InlineKeyboardButton("📈 Ce Trimestre", callback_data=f"{context}_period_quarter")
            ],
            [
                InlineKeyboardButton("📋 Cette Année", callback_data=f"{context}_period_year"),
                InlineKeyboardButton("🗓️ Personnalisé", callback_data=f"{context}_period_custom")
            ],
            [
                InlineKeyboardButton("🔙 Retour", callback_data="analytics_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def quick_actions(user_role: str = "user") -> InlineKeyboardMarkup:
        """Quick actions keyboard based on user role"""
        keyboard = [
            [
                InlineKeyboardButton("➕ Nouvelle Tâche", callback_data="quick_create_task"),
                InlineKeyboardButton("📋 Mes Tâches", callback_data="quick_my_tasks")
            ],
            [
                InlineKeyboardButton("🔍 Rechercher", callback_data="quick_search"),
                InlineKeyboardButton("⏰ En Retard", callback_data="quick_overdue")
            ]
        ]
        
        if user_role in ["admin", "manager"]:
            keyboard.append([
                InlineKeyboardButton("📊 Statistiques", callback_data="quick_stats"),
                InlineKeyboardButton("👥 Équipe", callback_data="quick_team")
            ])
        
        if user_role == "admin":
            keyboard.append([
                InlineKeyboardButton("⚙️ Admin", callback_data="admin_menu")
            ])
        
        keyboard.append([
            InlineKeyboardButton("⚙️ Paramètres", callback_data="settings_menu")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def pagination(
        current_page: int,
        total_pages: int,
        callback_prefix: str,
        items_per_page: int = 5
    ) -> List[InlineKeyboardButton]:
        """Generate pagination buttons"""
        buttons = []
        
        # First page
        if current_page > 1:
            buttons.append(
                InlineKeyboardButton("⏮️", callback_data=f"{callback_prefix}_page_0")
            )
        
        # Previous page
        if current_page > 0:
            buttons.append(
                InlineKeyboardButton("⬅️", callback_data=f"{callback_prefix}_page_{current_page-1}")
            )
        
        # Current page indicator
        buttons.append(
            InlineKeyboardButton(f"{current_page + 1}/{total_pages}", callback_data="noop")
        )
        
        # Next page
        if current_page < total_pages - 1:
            buttons.append(
                InlineKeyboardButton("➡️", callback_data=f"{callback_prefix}_page_{current_page+1}")
            )
        
        # Last page
        if current_page < total_pages - 2:
            buttons.append(
                InlineKeyboardButton("⏭️", callback_data=f"{callback_prefix}_page_{total_pages-1}")
            )
        
        return buttons
    
    @staticmethod
    def confirmation_dialog(
        action: str,
        item_id: str,
        message: str = "Êtes-vous sûr ?"
    ) -> InlineKeyboardMarkup:
        """Generic confirmation dialog"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirmer", callback_data=f"confirm_{action}_{item_id}"),
                InlineKeyboardButton("❌ Annuler", callback_data=f"cancel_{action}_{item_id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def language_selector() -> InlineKeyboardMarkup:
        """Language selection keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("🇫🇷 Français", callback_data="set_lang_fr"),
                InlineKeyboardButton("🇺🇸 English", callback_data="set_lang_en")
            ],
            [
                InlineKeyboardButton("🇲🇦 العربية", callback_data="set_lang_ar")
            ],
            [
                InlineKeyboardButton("🔙 Retour", callback_data="settings_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def help_menu() -> InlineKeyboardMarkup:
        """Help and support menu"""
        keyboard = [
            [
                InlineKeyboardButton("📚 Guide d'utilisation", callback_data="help_guide"),
                InlineKeyboardButton("❓ FAQ", callback_data="help_faq")
            ],
            [
                InlineKeyboardButton("🎥 Tutoriels", callback_data="help_tutorials"),
                InlineKeyboardButton("📞 Contact", callback_data="help_contact")
            ],
            [
                InlineKeyboardButton("🐛 Signaler Bug", callback_data="help_bug_report"),
                InlineKeyboardButton("💡 Suggestion", callback_data="help_suggestion")
            ],
            [
                InlineKeyboardButton("ℹ️ À propos", callback_data="help_about"),
                InlineKeyboardButton("🔄 Mises à jour", callback_data="help_updates")
            ],
            [
                InlineKeyboardButton("🏠 Menu Principal", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def dynamic_keyboard(
        items: List[Dict],
        callback_prefix: str,
        display_key: str = "name",
        id_key: str = "id",
        columns: int = 1,
        max_items: int = 10
    ) -> InlineKeyboardMarkup:
        """Generate dynamic keyboard from list of items"""
        keyboard = []
        
        # Limit items
        items = items[:max_items]
        
        # Group items by columns
        for i in range(0, len(items), columns):
            row = []
            for j in range(columns):
                if i + j < len(items):
                    item = items[i + j]
                    text = item.get(display_key, "N/A")
                    callback_data = f"{callback_prefix}_{item.get(id_key)}"
                    
                    # Truncate text if too long
                    if len(text) > 30:
                        text = text[:27] + "..."
                    
                    row.append(InlineKeyboardButton(text, callback_data=callback_data))
            
            if row:
                keyboard.append(row)
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def remove_keyboard():
        """Remove custom keyboard"""
        from telegram import ReplyKeyboardRemove
        return ReplyKeyboardRemove()
    
    @staticmethod
    def contact_keyboard() -> ReplyKeyboardMarkup:
        """Contact sharing keyboard"""
        keyboard = [
            [KeyboardButton("📱 Partager Contact", request_contact=True)],
            [KeyboardButton("📍 Partager Position", request_location=True)],
            [KeyboardButton("🔙 Retour")]
        ]
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )


# Utility functions for keyboard management
class KeyboardUtils:
    """Utility functions for keyboard operations"""
    
    @staticmethod
    def add_back_button(
        keyboard: List[List[InlineKeyboardButton]],
        callback_data: str = "main_menu",
        text: str = "🏠 Menu Principal"
    ) -> List[List[InlineKeyboardButton]]:
        """Add back button to existing keyboard"""
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
        return keyboard
    
    @staticmethod
    def split_long_keyboard(
        buttons: List[InlineKeyboardButton],
        max_per_row: int = 2,
        max_rows: int = 8
    ) -> List[List[InlineKeyboardButton]]:
        """Split long list of buttons into rows"""
        keyboard = []
        total_buttons = min(len(buttons), max_per_row * max_rows)
        
        for i in range(0, total_buttons, max_per_row):
            row = buttons[i:i + max_per_row]
            keyboard.append(row)
        
        return keyboard
    
    @staticmethod
    def create_numbered_list(
        items: List[str],
        callback_prefix: str,
        start_index: int = 0
    ) -> InlineKeyboardMarkup:
        """Create numbered list keyboard"""
        keyboard = []
        
        for i, item in enumerate(items):
            number = start_index + i + 1
            text = f"{number}. {item}"
            if len(text) > 35:
                text = text[:32] + "..."
            
            keyboard.append([
                InlineKeyboardButton(
                    text,
                    callback_data=f"{callback_prefix}_{i}"
                )
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def merge_keyboards(
        *keyboards: InlineKeyboardMarkup
    ) -> InlineKeyboardMarkup:
        """Merge multiple keyboards into one"""
        merged_keyboard = []
        
        for keyboard in keyboards:
            if keyboard and keyboard.inline_keyboard:
                merged_keyboard.extend(keyboard.inline_keyboard)
        
        return InlineKeyboardMarkup(merged_keyboard)


# Export keyboard classes and utilities
__all__ = [
    'BotKeyboards',
    'KeyboardUtils'
]