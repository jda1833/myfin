from flask import Blueprint
from .user import settings, update_email, update_password, update_coinbase_credentials
from .coinbase_transactions import export_transactions, import_transactions, clear_transactions
from .fidelity_transactions import export_fidelity_transactions, import_fidelity_transactions, clear_fidelity_transactions

settings_bp = Blueprint('settings', __name__)

# Register routes
settings_bp.route('/settings', methods=['GET', 'POST'])(settings)
settings_bp.route('/update_email', methods=['POST'])(update_email)
settings_bp.route('/update_password', methods=['POST'])(update_password)
settings_bp.route('/update_coinbase_credentials', methods=['POST'])(update_coinbase_credentials)
settings_bp.route('/export_transactions', methods=['POST'])(export_transactions)
settings_bp.route('/import_transactions', methods=['POST'])(import_transactions)
settings_bp.route('/clear_transactions', methods=['POST'])(clear_transactions)
settings_bp.route('/export_fidelity_transactions', methods=['POST'])(export_fidelity_transactions)
settings_bp.route('/import_fidelity_transactions', methods=['POST'])(import_fidelity_transactions)
settings_bp.route('/clear_fidelity_transactions', methods=['POST'])(clear_fidelity_transactions)