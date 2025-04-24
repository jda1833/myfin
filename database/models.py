from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet
import os

# Load secret configuration
try:
    from config import ENCRYPTION_KEY
except ImportError:
    raise Exception("config.py not found. Please create config.py with ENCRYPTION_KEY.")

# Initialize SQLAlchemy (will be bound to the app in app/__init__.py)
db = SQLAlchemy()

# Encryption setup
fernet = Fernet(ENCRYPTION_KEY)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    totp_secret = db.Column(db.String(32), nullable=True)
    coinbase_api_key = db.Column(db.String(200), nullable=True)  # Encrypted
    coinbase_api_secret = db.Column(db.String(200), nullable=True)  # Encrypted
    transactions = db.relationship('Transaction', backref='user', lazy=True)

    def set_coinbase_api_key(self, api_key):
        """Encrypt and store Coinbase API key."""
        if api_key:
            self.coinbase_api_key = fernet.encrypt(api_key.encode()).decode()
        else:
            self.coinbase_api_key = None

    def get_coinbase_api_key(self):
        """Decrypt and return Coinbase API key."""
        if self.coinbase_api_key:
            return fernet.decrypt(self.coinbase_api_key.encode()).decode()
        return None

    def set_coinbase_api_secret(self, api_secret):
        """Encrypt and store Coinbase API secret."""
        if api_secret:
            self.coinbase_api_secret = fernet.encrypt(api_secret.encode()).decode()
        else:
            self.coinbase_api_secret = None

    def get_coinbase_api_secret(self):
        """Decrypt and return Coinbase API secret."""
        if self.coinbase_api_secret:
            return fernet.decrypt(self.coinbase_api_secret.encode()).decode()
        return None

# Transaction model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coinbase_tx_id = db.Column(db.String(100), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    price_at_transaction = db.Column(db.Float, nullable=True)  # New column for USD price