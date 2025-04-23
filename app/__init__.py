import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from database.models import db
from app.routes.auth import auth_bp
from app.routes.main import main_bp
from app.routes.coinbase import coinbase_bp  # New blueprint

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure random key

    # Define the database path and ensure the database folder exists
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))  # Root of flask_app/
    db_path = os.path.join(basedir, 'database', 'users.db')
    os.makedirs(os.path.join(basedir, 'database'), exist_ok=True)  # Create database folder if it doesn't exist
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Bind SQLAlchemy to the app
    db.init_app(app)

    # Create database within app context
    with app.app_context():
        db.create_all()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(coinbase_bp)  # Register new blueprint

    return app