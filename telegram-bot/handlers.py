#!/usr/bin/env python3
# ===================================================================
# telegram-bot/enhanced_handlers.py - Complete Telegram Bot Handlers
# ===================================================================

import os
import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import io
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode, ChatAction
import requests
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import seaborn as sns

from .base_handlers import BaseHandler
from .keyboards import BotKeyboards
from .messages import BotMessages
from .decorators import require_auth, rate_limit, require_admin
from .utils import format_task_summary, send_long_message, escape_markdown
from .exceptions import APIException, BotException

logger = logging.getLogger(__name__)

# Conversation states
TASK_PO, TASK_DESCRIPTION, TASK_CUSTOMER, TASK_REQUESTER = range(4)
TASK_RESPONSIBLE, TASK_CATEGORY, TASK_PRIORITY, TASK_DEADLINE = range(4, 8)
TASK_NOTES, SEARCH_TERM, WAITING_FILE, WAITING_NOTE = range(8, 12)
EXPORT_FORMAT, EXPORT_FILTERS, SETTINGS_MENU = range(12, 15)

class EnhancedFileHandlers(BaseHandler):
    """Enhanced file handling capabilities"""
    
    @staticmethod
    @require_auth
    @rate_limit
    async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads"""
        try:
            document = update.message.document
            
            # Check file type
            file_name = document.file_name.lower()
            if not any(file_name.endswith(ext) for ext in ['.xlsx', '.xls', '.csv', '.txt']):
                await update.message.reply_text(
                    "❌ Type de fichier non supporté. Formats acceptés: Excel (.xlsx, .xls), CSV (.csv), Texte (.txt)",
                    reply_markup=BotKeyboards.main_menu()
                )
                return
                
            # Check file size (max 20MB)
            if document.file_size > 20 * 1024 * 1024:
                await update.message.reply_text(
                    "❌ Fichier trop volumineux. Taille maximale: 20MB",
                    reply_markup=BotKeyboards.main_menu()
                )
                return
                
            await update.message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT)
            
            # Download file
            file = await context.bot.get_file(document.file_id)
            file_path = f"/tmp/{document.file_name}"
            await file.download_to_drive(file_path)
            
            # Process based on file type
            if file_name.endswith(('.xlsx', '.xls')):
                result = await EnhancedFileHandlers._process_excel_file(file_path, update, context)
            elif file_name.endswith('.csv'):
                result = await EnhancedFileHandlers._process_csv_file(file_path, update, context)
            else:
                result = await EnhancedFileHandlers._process_text_file(file_path, update, context)
                
            # Clean up
            if os.path.exists(file_path):
                os