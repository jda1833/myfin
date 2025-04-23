from flask import Blueprint, render_template, redirect, url_for, session, flash
from database.models import db, User, Transaction
from coinbase.wallet.client import Client
from coinbase.wallet.error import APIError
from datetime import datetime
import os

coinbase_bp = Blueprint('coinbase', __name__)

@coinbase_bp.route('/transactions')
def transactions():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    # Initialize Coinbase client
    try:
        client = Client(
            api_key=os.getenv('COINBASE_API_KEY', 'your_coinbase_api_key'),
            api_secret=os.getenv('COINBASE_API_SECRET', 'your_coinbase_api_secret')
        )
    except Exception as e:
        flash(f'Failed to initialize Coinbase client: {str(e)}', 'error')
        return redirect(url_for('main.home'))

    # Fetch accounts
    try:
        accounts = client.get_accounts()
    except APIError as e:
        flash(f'Failed to fetch Coinbase accounts: {str(e)}', 'error')
        return redirect(url_for('main.home'))

    # Fetch and store transactions for each account
    for account in accounts.data:
        try:
            # Handle pagination for transactions
            txs = client.get_transactions(account.id)
            for tx in txs.data:
                # Check if transaction already exists
                existing_tx = Transaction.query.filter_by(coinbase_tx_id=tx.id).first()
                if not existing_tx:
                    # Parse transaction details
                    amount = float(tx.amount.amount)
                    currency = tx.amount.currency
                    tx_type = tx.type
                    timestamp = datetime.strptime(tx.created_at, '%Y-%m-%dT%H:%M:%SZ')
                    status = tx.status

                    # Store transaction in database
                    new_tx = Transaction(
                        coinbase_tx_id=tx.id,
                        user_id=user.id,
                        type=tx_type,
                        amount=amount,
                        currency=currency,
                        timestamp=timestamp,
                        status=status
                    )
                    db.session.add(new_tx)
            db.session.commit()
        except APIError as e:
            flash(f'Failed to fetch transactions for account {account.id}: {str(e)}', 'error')
            continue

    # Retrieve user's transactions from database
    user_transactions = Transaction.query.filter_by(user_id=user.id).all()

    return render_template('transactions.html', transactions=user_transactions)