from flask import Blueprint, render_template, session, redirect, url_for
from database.models import db, User, Transaction
from sqlalchemy import func

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect(url_for('auth.login'))

    # Crypto balances (source='coinbase')
    crypto_balances = (
        db.session.query(
            Transaction.currency,
            func.sum(Transaction.amount).label('total_amount')
        )
        .filter_by(user_id=user.id, source='coinbase')
        .group_by(Transaction.currency)
        .having(func.sum(Transaction.amount) != 0)
        .order_by(Transaction.currency)
        .all()
    )
    formatted_crypto_balances = [
        {'currency': balance.currency, 'amount': f"{balance.total_amount:.8f}"}
        for balance in crypto_balances
    ]

    # Stock balances (source='fidelity')
    stock_balances = (
        db.session.query(
            Transaction.currency,
            func.sum(Transaction.amount).label('total_amount')
        )
        .filter_by(user_id=user.id, source='fidelity')
        .group_by(Transaction.currency)
        .having(func.sum(Transaction.amount) != 0)
        .order_by(Transaction.currency)
        .all()
    )
    formatted_stock_balances = [
        {'currency': balance.currency, 'amount': f"{balance.total_amount:.2f}"}
        for balance in stock_balances
    ]

    return render_template(
        'index.html',
        user=user,
        crypto_balances=formatted_crypto_balances,
        stock_balances=formatted_stock_balances
    )