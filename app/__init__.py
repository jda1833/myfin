import os
from flask import Flask, session  # Added session import
from flask_sqlalchemy import SQLAlchemy
from database.models import db
from app.routes.auth import auth_bp
from app.routes.main import main_bp
from app.routes.coinbase import coinbase_bp
from app.routes.settings import settings_bp
import secrets

def create_app():
    app = Flask(__name__)

    # Load secret configuration from config.py if it exists
    try:
        from config import SECRET_KEY
        app.config['SECRET_KEY'] = SECRET_KEY
    except ImportError:
        app.config['SECRET_KEY'] = 'your_secret_key'
        print("Warning: config.py not found. Using default SECRET_KEY.")

    # Define the database path and ensure the database folder exists
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.path.join(basedir, 'database', 'users.db')
    os.makedirs(os.path.join(basedir, 'database'), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Generate a CSRF token for AJAX requests (basic implementation)
    @app.before_request
    def set_csrf_token():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(16)

    # Bind SQLAlchemy to the app
    db.init_app(app)

    # Create database within app context
    with app.app_context():
        db.create_all()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(coinbase_bp)
    app.register_blueprint(settings_bp)

    return app