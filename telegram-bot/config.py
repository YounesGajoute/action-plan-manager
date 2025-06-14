# ===================================================================
# telegram-bot/config.py
# ===================================================================
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class TelegramBotSettings(BaseSettings):
    """Telegram Bot Configuration Settings"""
    
    # Telegram Bot Configuration
    bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    webhook_url: Optional[str] = Field(None, env="TELEGRAM_WEBHOOK_URL")
    webhook_secret: Optional[str] = Field(None, env="TELEGRAM_WEBHOOK_SECRET")
    webhook_port: int = Field(8443, env="TELEGRAM_WEBHOOK_PORT")
    
    # API Configuration
    api_base_url: str = Field("http://localhost:5000", env="API_BASE_URL")
    api_timeout: int = Field(30, env="API_TIMEOUT")
    
    # Database Configuration
    database_url: str = Field(
        "postgresql://actionplan:password@localhost:5432/actionplan",
        env="DATABASE_URL"
    )
    
    # Redis Configuration
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    
    # Microsoft Graph Configuration
    ms_tenant_id: str = Field(..., env="MS_TENANT_ID")
    ms_client_id: str = Field(..., env="MS_CLIENT_ID")
    ms_client_secret: str = Field(..., env="MS_CLIENT_SECRET")
    ms_authority: str = Field(..., env="MS_AUTHORITY")
    
    # Security Settings
    jwt_secret: str = Field(..., env="JWT_SECRET")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    
    # Bot Behavior Settings
    max_message_length: int = Field(4096, env="MAX_MESSAGE_LENGTH")
    max_inline_buttons: int = Field(8, env="MAX_INLINE_BUTTONS")
    session_timeout: int = Field(3600, env="SESSION_TIMEOUT")  # 1 hour
    
    # Notification Settings
    enable_notifications: bool = Field(True, env="ENABLE_NOTIFICATIONS")
    notification_check_interval: int = Field(60, env="NOTIFICATION_CHECK_INTERVAL")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("logs/telegram_bot.log", env="LOG_FILE")
    
    # Task Management Settings
    max_tasks_per_page: int = Field(10, env="MAX_TASKS_PER_PAGE")
    task_update_interval: int = Field(300, env="TASK_UPDATE_INTERVAL")  # 5 minutes
    
    # Allowed Users (comma-separated Telegram usernames or user IDs)
    allowed_users: List[str] = Field(default_factory=list, env="ALLOWED_USERS")
    admin_users: List[str] = Field(default_factory=list, env="ADMIN_USERS")
    
    # Features Configuration
    enable_file_upload: bool = Field(True, env="ENABLE_FILE_UPLOAD")
    enable_task_creation: bool = Field(True, env="ENABLE_TASK_CREATION")
    enable_task_updates: bool = Field(True, env="ENABLE_TASK_UPDATES")
    enable_analytics: bool = Field(True, env="ENABLE_ANALYTICS")
    
    # Rate Limiting
    rate_limit_per_user: int = Field(60, env="RATE_LIMIT_PER_USER")  # requests per minute
    rate_limit_window: int = Field(60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # Timezone Settings
    timezone: str = Field("Africa/Casablanca", env="TIMEZONE")
    
    # Development Settings
    debug: bool = Field(False, env="DEBUG")
    environment: str = Field("production", env="ENVIRONMENT")
    
    @validator("allowed_users", "admin_users", pre=True)
    def parse_user_lists(cls, v):
        if isinstance(v, str):
            return [user.strip() for user in v.split(",") if user.strip()]
        return v or []
    
    @validator("bot_token")
    def validate_bot_token(cls, v):
        if not v or not v.startswith(("bot", "BOT")):
            raise ValueError("Invalid Telegram bot token format")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Bot Messages and Responses
class BotMessages:
    """Centralized bot messages and responses"""
    
    # Welcome and Help Messages
    WELCOME = """
👋 **Bienvenue sur le Bot Action Plan TechMac!**

Je suis votre assistant pour la gestion des plans d'action. Voici ce que je peux faire pour vous :

📋 **Gestion des Tâches:**
• Consulter vos tâches
• Créer de nouvelles tâches
• Mettre à jour le statut des tâches
• Rechercher des tâches

📊 **Analyses et Rapports:**
• Voir les statistiques de performance
• Obtenir des rapports personnalisés
• Suivre les échéances

🔔 **Notifications:**
• Recevoir des alertes de tâches
• Rappels d'échéances
• Mises à jour en temps réel

Pour commencer, utilisez /help pour voir toutes les commandes disponibles.
    """
    
    HELP = """
📚 **Commandes Disponibles:**

**📋 Gestion des Tâches:**
• `/tasks` - Voir vos tâches
• `/create` - Créer une nouvelle tâche
• `/update` - Mettre à jour une tâche
• `/search <terme>` - Rechercher des tâches

**📊 Analyses:**
• `/stats` - Statistiques générales
• `/dashboard` - Tableau de bord
• `/overdue` - Tâches en retard

**⚙️ Paramètres:**
• `/settings` - Gérer vos préférences
• `/notifications` - Paramètres de notification
• `/profile` - Voir votre profil

**ℹ️ Aide:**
• `/help` - Afficher cette aide
• `/about` - À propos du bot
• `/contact` - Contacter le support

Tapez simplement la commande pour commencer !
    """
    
    # Error Messages
    ERROR_GENERIC = "❌ Une erreur s'est produite. Veuillez réessayer."
    ERROR_UNAUTHORIZED = "🚫 Vous n'êtes pas autorisé à utiliser cette commande."
    ERROR_NOT_FOUND = "🔍 Aucun résultat trouvé pour votre recherche."
    ERROR_INVALID_FORMAT = "📝 Format de données invalide. Veuillez vérifier votre saisie."
    ERROR_API_CONNECTION = "🌐 Impossible de se connecter au serveur. Veuillez réessayer plus tard."
    ERROR_RATE_LIMIT = "⏰ Trop de requêtes. Veuillez patienter un moment."
    
    # Success Messages
    SUCCESS_TASK_CREATED = "✅ Tâche créée avec succès !"
    SUCCESS_TASK_UPDATED = "✅ Tâche mise à jour avec succès !"
    SUCCESS_TASK_DELETED = "✅ Tâche supprimée avec succès !"
    SUCCESS_SETTINGS_SAVED = "✅ Paramètres sauvegardés avec succès !"
    
    # Status Messages
    PROCESSING = "⏳ Traitement en cours..."
    LOADING = "📊 Chargement des données..."
    SEARCHING = "🔍 Recherche en cours..."


# Bot Command Definitions
class BotCommands:
    """Bot command definitions and metadata"""
    
    COMMANDS = [
        ("start", "Démarrer le bot"),
        ("help", "Afficher l'aide"),
        ("tasks", "Voir les tâches"),
        ("create", "Créer une tâche"),
        ("update", "Mettre à jour une tâche"),
        ("search", "Rechercher des tâches"),
        ("stats", "Statistiques"),
        ("dashboard", "Tableau de bord"),
        ("overdue", "Tâches en retard"),
        ("settings", "Paramètres"),
        ("notifications", "Notifications"),
        ("profile", "Profil utilisateur"),
        ("about", "À propos"),
        ("contact", "Contact support"),
    ]
    
    ADMIN_COMMANDS = [
        ("admin", "Panneau d'administration"),
        ("users", "Gestion des utilisateurs"),
        ("logs", "Consulter les logs"),
        ("broadcast", "Diffuser un message"),
        ("backup", "Sauvegarder les données"),
    ]


# Keyboard Layouts
class KeyboardLayouts:
    """Predefined keyboard layouts for bot interactions"""
    
    MAIN_MENU = [
        ["📋 Mes Tâches", "➕ Nouvelle Tâche"],
        ["📊 Statistiques", "🔍 Rechercher"],
        ["⚙️ Paramètres", "ℹ️ Aide"]
    ]
    
    TASK_ACTIONS = [
        ["✏️ Modifier", "✅ Marquer Terminé"],
        ["📝 Ajouter Note", "🗑️ Supprimer"],
        ["🏠 Menu Principal"]
    ]
    
    TASK_STATUS = [
        ["En Attente", "En Cours"],
        ["Terminé", "Annulé"],
        ["En Pause"]
    ]
    
    TASK_PRIORITY = [
        ["🔴 Urgent", "🟠 Élevé"],
        ["🟡 Moyen", "🟢 Faible"]
    ]
    
    TASK_CATEGORIES = [
        ["🔧 Installation", "🛠️ Réparation"],
        ["💻 Développement", "🚚 Livraison"],
        ["💼 Commercial"]
    ]
    
    SETTINGS_MENU = [
        ["🔔 Notifications", "🌐 Langue"],
        ["⏰ Fuseau Horaire", "🎨 Thème"],
        ["🏠 Menu Principal"]
    ]


# Global settings instance
settings = TelegramBotSettings()