from flask import Blueprint
from .login import login, logout
from .register import register
from .twofa import setup_2fa, verify_2fa, disable_2fa

auth_bp = Blueprint('auth', __name__)

# Register routes
auth_bp.route('/login', methods=['GET', 'POST'])(login)
auth_bp.route('/logout')(logout)
auth_bp.route('/register', methods=['GET', 'POST'])(register)
auth_bp.route('/setup_2fa', methods=['GET'])(setup_2fa)
auth_bp.route('/verify_2fa', methods=['GET', 'POST'])(verify_2fa)
auth_bp.route('/disable_2fa', methods=['POST'])(disable_2fa)