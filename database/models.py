from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet
import config

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    coinbase_api_key = db.Column(db.String(200))
    coinbase_api_secret = db.Column(db.String(200))
    totp_secret = db.Column(db.String(100))

    def set_coinbase_api_key(self, api_key):
        f = Fernet(config.ENCRYPTION_KEY)
        self.coinbase_api_key = f.encrypt(api_key.encode()).decode()

    def get_coinbase_api_key(self):
        f = Fernet(config.ENCRYPTION_KEY)
        return f.decrypt(self.coinbase_api_key.encode()).decode()

    def set_coinbase_api_secret(self, api_secret):
        f = Fernet(config.ENCRYPTION_KEY)
        self.coinbase_api_secret = f.encrypt(api_secret.encode()).decode()

    def get_coinbase_api_secret(self):
        f = Fernet(config.ENCRYPTION_KEY)
        return f.decrypt(self.coinbase_api_secret.encode()).decode()

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coinbase_tx_id = db.Column(db.String(100), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    price_at_transaction = db.Column(db.Float)
    source = db.Column(db.String(20), nullable=False, default='coinbase')