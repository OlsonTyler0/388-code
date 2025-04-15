# src/routes/__init__.py
from .main import main_bp
from .auth import auth_bp
from .sentiment import sentiment_bp
from .storage import storage_bp
from .youtube import youtube_bp
from .analysis import analysis_bp
from .admin import admin_bp

# Export all blueprints
__all__ = ['main_bp', 'auth_bp', 'sentiment_bp', 'storage_bp', 'youtube_bp', 'analysis_bp', 'admin_bp']