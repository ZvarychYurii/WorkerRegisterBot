import os
from typing import Optional, List

class Config:
    """Configuration class for the bot"""
    
    def __init__(self):
        # Bot token (required)
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        # Admin chat IDs (список админов)
        admin_ids_str = os.getenv("ADMIN_CHAT_IDS", "")
        self.ADMIN_CHAT_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip().isdigit()]
        
        # Google Sheets configuration
        self.GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        self.GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Worker Registrations")
        self.ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
        
        # Bot settings
        self.MAX_NAME_LENGTH = int(os.getenv("MAX_NAME_LENGTH", "50"))
        self.MIN_AGE = int(os.getenv("MIN_AGE", "16"))
        self.MAX_AGE = int(os.getenv("MAX_AGE", "70"))
        
        # Logging level
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration settings"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        
        if self.MIN_AGE >= self.MAX_AGE:
            raise ValueError("MIN_AGE must be less than MAX_AGE")
        
        if self.MAX_NAME_LENGTH < 2:
            raise ValueError("MAX_NAME_LENGTH must be at least 2")
    
    @property
    def is_sheets_configured(self) -> bool:
        """Check if Google Sheets is properly configured"""
        return bool(self.GOOGLE_SHEETS_CREDENTIALS)
    
    @property
    def is_admin_configured(self) -> bool:
        """Check if admin notifications are configured"""
        return len(self.ADMIN_CHAT_IDS) > 0
    
    def get_env_status(self) -> dict:
        """Get status of environment configuration"""
        return {
            "bot_token_configured": bool(self.BOT_TOKEN),
            "admin_chat_configured": self.is_admin_configured,
            "google_sheets_configured": self.is_sheets_configured,
            "admin_email_configured": bool(self.ADMIN_EMAIL),
        }
