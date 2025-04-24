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

    # Calculate non-zero balances per currency
    balances = (
        db.session.query(
            Transaction.currency,
            func.sum(Transaction.amount).label('total_amount')
        )
        .filter_by(user_id=user.id)
        .group_by(Transaction.currency)
        .having(func.sum(Transaction.amount) > 0.0001)
        .order_by(Transaction.currency)
        .all()
    )

    # Format balances for display (8 decimal places)
    formatted_balances = [
        {'currency': balance.currency, 'amount': f"{balance.total_amount:.8f}"}
        for balance in balances
    ]

    return render_template('index.html', user=user, balances=formatted_balances)