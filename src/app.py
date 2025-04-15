# ╔═══════════════════════════════════════════════════════════╗
#   app.py
#       Initalizes the application for the webiste.
# ╚═══════════════════════════════════════════════════════════╝

from flask import Flask
from flask_login import LoginManager
from datetime import datetime
import logging
import os
from src.models import db, User
from werkzeug.security import generate_password_hash
from src.routes import (
    main_bp,
    auth_bp,
    sentiment_bp, 
    storage_bp,
    youtube_bp,
    analysis_bp,
    admin_bp
)
from src.utils.filters import format_date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key_here')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(sentiment_bp)
    app.register_blueprint(storage_bp)
    app.register_blueprint(youtube_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(admin_bp)

    # Register template filters
    app.template_filter('format_date')(format_date)

    # Register context processors
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    # Initialize database and create admin user
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin-password'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()

    return app