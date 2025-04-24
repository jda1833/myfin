from flask import Blueprint
from .transactions import transactions
from .import_transactions import import_transactions

fidelity_bp = Blueprint('fidelity', __name__)

# Register routes
fidelity_bp.route('/transactions')(transactions)
fidelity_bp.route('/import_transactions', methods=['GET', 'POST'])(import_transactions)