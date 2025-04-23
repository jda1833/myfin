from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy (will be bound to the app in app/__init__.py)
db = SQLAlchemy()

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    totp_secret = db.Column(db.String(32), nullable=True)  # Stores TOTP secret for 2FA
    transactions = db.relationship('Transaction', backref='user', lazy=True)  # One-to-many with Transaction

# Transaction model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coinbase_tx_id = db.Column(db.String(100), unique=True, nullable=False)  # Coinbase transaction ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Link to User
    type = db.Column(db.String(50), nullable=False)  # e.g., 'buy', 'sell', 'send', 'receive'
    amount = db.Column(db.Float, nullable=False)  # Transaction amount
    currency = db.Column(db.String(10), nullable=False)  # e.g., 'BTC', 'ETH'
    timestamp = db.Column(db.DateTime, nullable=False)  # Transaction time
    status = db.Column(db.String(50), nullable=False)  # e.g., 'completed', 'pending'