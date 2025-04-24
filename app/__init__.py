from flask import Flask
from database.models import db
from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.coinbase import coinbase_bp
from app.routes.fidelity import fidelity_bp
from app.routes.settings import settings_bp

def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crypto.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(coinbase_bp, url_prefix='/coinbase')
    app.register_blueprint(fidelity_bp, url_prefix='/fidelity')
    app.register_blueprint(settings_bp)

    return app