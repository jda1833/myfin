# app/models.py
# Defines the User model with encrypted Coinbase API keys.
# python
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from cryptography.fernet import Fernet
import os

Base = declarative_base()

# Generate or load encryption key
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key().decode())
cipher = Fernet(ENCRYPTION_KEY)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # Hashed
    email = Column(String, nullable=False)
    totp_secret = Column(String, nullable=False)
    coinbase_api_key = Column(String)  # Encrypted
    coinbase_api_secret = Column(String)  # Encrypted

    def set_api_keys(self, api_key, api_secret):
        self.coinbase_api_key = cipher.encrypt(api_key.encode()).decode()
        self.coinbase_api_secret = cipher.encrypt(api_secret.encode()).decode()

    def get_api_keys(self):
        if self.coinbase_api_key and self.coinbase_api_secret:
            return (
                cipher.decrypt(self.coinbase_api_key.encode()).decode(),
                cipher.decrypt(self.coinbase_api_secret.encode()).decode()
            )
        return None, None
