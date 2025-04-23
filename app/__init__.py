# app/__init__.py
# Initializes the Flask app and database.
# python

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '097c67bf1ea33c85855764ab5e13b68501b382d2a90f4873'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/user.db'
    
    # Initialize database
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], echo=True)
    Base = declarative_base()
    # Create tables for all defined models
    with app.app_context():  # Ensure app context is active
        Base.metadata.create_all(engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    app.config['DB_SESSION'] = Session()
    
    # Register routes
    from .routes import bp
    app.register_blueprint(bp)
    
        # Clean up session after each request
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        current_app.config['DB_SESSION'].remove()

    return app

    

