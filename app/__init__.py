# app/__init__.py
# Initializes the Flask app and database.
# python

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secure_secret_key'  # Replace or use environment variable
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    
    # Initialize database
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], echo=False)
    Base = declarative_base()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    app.config['DB_SESSION'] = Session()
    
    # Register routes
    from .routes import bp
    app.register_blueprint(bp)
    
    return app
