from flask import render_template, redirect, url_for, session, flash, request
from database.models import db, User, Transaction
from sqlalchemy import func
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='log.txt')
logger = logging.getLogger(__name__)

def transactions():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    # Get query parameters
    currency = request.args.get('currency', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Transactions per page

    # Base query for transactions
    query = Transaction.query.filter_by(user_id=user.id, source='fidelity')

    # Apply currency filter
    if currency:
        query = query.filter_by(currency=currency)

    # Paginate results
    pagination = query.order_by(Transaction.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items

    # Get unique currencies (stock symbols) for filter dropdown
    currencies = db.session.query(Transaction.currency).filter_by(user_id=user.id, source='fidelity').distinct().all()
    currencies = [c[0] for c in currencies]

    # Prepare chart data (cumulative amount owned by date)
    chart_query = Transaction.query.filter_by(user_id=user.id, source='fidelity')
    if currency:
        chart_query = chart_query.filter_by(currency=currency)

    # Fetch transactions ordered by timestamp
    chart_transactions = (
        chart_query
        .filter(Transaction.type.in_(['Buy', 'Sell']))
        .with_entities(
            func.date(Transaction.timestamp).label('date'),
            Transaction.amount,
            Transaction.type
        )
        .order_by(Transaction.timestamp)
        .all()
    )

    # Calculate cumulative amount owned by date
    balance = 0
    chart_data = {}
    for tx in chart_transactions:
        date = tx.date
        amount = tx.amount
        balance += amount
        chart_data[date] = balance

    # Format chart data for Chart.js
    chart_labels = sorted(chart_data.keys())
    chart_values = [float(chart_data[date]) for date in chart_labels]
    chart_data_dict = {'labels': chart_labels, 'values': chart_values}

    return render_template(
        'fidelity_transactions.html',
        transactions=transactions,
        currencies=currencies,
        currency=currency,
        pagination=pagination,
        chart_data=chart_data_dict
    )