from flask import Blueprint, render_template, redirect, url_for, session, flash, request, jsonify
from database.models import db, User, Transaction
from coinbase.wallet.client import Client
from coinbase.wallet.error import APIError
from datetime import datetime
import pandas as pd
import logging
import os
import requests
from sqlalchemy import func

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

coinbase_bp = Blueprint('coinbase', __name__)

@coinbase_bp.route('/transactions')
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
    query = Transaction.query.filter_by(user_id=user.id)

    # Apply currency filter
    if currency:
        query = query.filter_by(currency=currency)

    # Paginate results
    pagination = query.order_by(Transaction.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items

    # Get unique currencies for filter dropdown
    currencies = db.session.query(Transaction.currency).filter_by(user_id=user.id).distinct().all()
    currencies = [c[0] for c in currencies]

    # Prepare chart data (cumulative amount owned by date)
    chart_query = (
        Transaction.query
        .filter_by(user_id=user.id)
        .filter(Transaction.type.in_(['buy', 'receive', 'sell', 'send']))  # Relevant transaction types
    )
    if currency:
        chart_query = chart_query.filter_by(currency=currency)

    # Fetch transactions ordered by timestamp
    chart_transactions = (
        chart_query
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
        tx_type = tx.type.lower()
        # Update balance based on transaction type
        if tx_type in ['buy', 'receive']:
            balance += amount
        elif tx_type in ['sell', 'send']:
            balance -= amount
        # Store balance for the date (last transaction of the day)
        chart_data[date] = balance

    # Format chart data for Chart.js
    chart_labels = sorted(chart_data.keys())
    chart_values = [float(chart_data[date]) for date in chart_labels]
    chart_data_dict = {'labels': chart_labels, 'values': chart_values}

    return render_template(
        'transactions.html',
        transactions=transactions,
        currencies=currencies,
        currency=currency,
        pagination=pagination,
        chart_data=chart_data_dict
    )

@coinbase_bp.route('/fetch_transactions', methods=['POST'])
def fetch_transactions():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Please log in.'}), 401

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404

    # Check for Coinbase API credentials
    try:
        api_key = user.get_coinbase_api_key()
        api_secret = user.get_coinbase_api_secret()
    except Exception as e:
        logger.error(f"Error decrypting Coinbase credentials: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to decrypt Coinbase API credentials.'}), 500

    if not api_key or not api_secret:
        return jsonify({'success': False, 'message': 'Please add Coinbase API credentials in Settings.'}), 400

    # Initialize Coinbase client
    try:
        client = Client(api_key=api_key, api_secret=api_secret)
    except Exception as e:
        logger.error(f"Failed to initialize Coinbase client: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to initialize Coinbase client: {str(e)}'}), 500

    # Fetch accounts
    try:
        accounts = client.get_accounts()
        logger.debug(f"Fetched accounts: {accounts}")
    except APIError as e:
        logger.error(f"Coinbase APIError fetching accounts: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to fetch Coinbase accounts: {str(e)}'}), 500
    except requests.exceptions.JSONDecodeError as e:
        logger.error(f"JSONDecodeError fetching accounts: {str(e)}")
        return jsonify({'success': False, 'message': 'Invalid response from Coinbase API. Please check your API credentials.'}), 500
    except Exception as e:
        logger.error(f"Unexpected error fetching accounts: {str(e)}")
        return jsonify({'success': False, 'message': f'Unexpected error fetching accounts: {str(e)}'}), 500

    # Fetch and store transactions
    imported_count = 0
    for account in accounts.data:
        try:
            txs = client.get_transactions(account.id)
            logger.debug(f"Fetched transactions for account {account.id}: {txs}")
            for tx in txs.data:
                existing_tx = Transaction.query.filter_by(coinbase_tx_id=tx.id).first()
                if not existing_tx:
                    amount = float(tx.amount.amount)
                    currency = tx.amount.currency
                    tx_type = tx.type
                    timestamp = datetime.strptime(tx.created_at, '%Y-%m-%dT%H:%M:%SZ')
                    status = tx.status
                    new_tx = Transaction(
                        coinbase_tx_id=tx.id,
                        user_id=user.id,
                        type=tx_type,
                        amount=amount,
                        currency=currency,
                        timestamp=timestamp,
                        status=status,
                        price_at_transaction=None
                    )
                    db.session.add(new_tx)
                    imported_count += 1
            db.session.commit()
        except APIError as e:
            logger.error(f"Coinbase APIError fetching transactions for account {account.id}: {str(e)}")
            continue
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"JSONDecodeError fetching transactions for account {account.id}: {str(e)}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error fetching transactions for account {account.id}: {str(e)}")
            continue

    if imported_count > 0:
        message = f'Successfully imported {imported_count} transactions.'
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': 'No new transactions imported.'})

@coinbase_bp.route('/import_transactions', methods=['GET', 'POST'])
def import_transactions():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # Check if a file was uploaded
        if 'csv_file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('coinbase.import_transactions'))

        file = request.files['csv_file']
        if not file or not file.filename.endswith('.csv'):
            flash('Please upload a valid CSV file.', 'error')
            return redirect(url_for('coinbase.import_transactions'))

        try:
            # Read CSV using pandas
            df = pd.read_csv(file)
            logger.debug(f"CSV columns: {df.columns.tolist()}")

            # Required Coinbase CSV columns
            required_columns = ['ID', 'Timestamp', 'Transaction Type', 'Asset', 'Quantity Transacted', 'Price at Transaction']
            if not all(col in df.columns for col in required_columns):
                flash('Invalid CSV format. Ensure it includes ID, Timestamp, Transaction Type, Asset, Quantity Transacted, and Price at Transaction.', 'error')
                return redirect(url_for('coinbase.import_transactions'))

            # Process each row
            imported_count = 0
            for index, row in df.iterrows():
                # Use the ID column for coinbase_tx_id
                tx_id = row['ID']
                if Transaction.query.filter_by(coinbase_tx_id=tx_id).first():
                    continue  # Skip duplicates

                try:
                    # Parse timestamp
                    timestamp = pd.to_datetime(row['Timestamp']).to_pydatetime()
                    # Parse Price at Transaction (e.g., "$45.67" -> 45.67)
                    price_str = row['Price at Transaction'].replace('$', '').replace(',', '')
                    price = float(price_str)
                    # Map CSV fields to Transaction model
                    new_tx = Transaction(
                        coinbase_tx_id=tx_id,
                        user_id=user.id,
                        type=row['Transaction Type'].lower(),
                        amount=float(row['Quantity Transacted']),
                        currency=row['Asset'],
                        timestamp=timestamp,
                        status='completed',
                        price_at_transaction=price
                    )
                    db.session.add(new_tx)
                    imported_count += 1
                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing row {index}: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error processing row {index}: {str(e)}")
                    continue

            db.session.commit()
            flash(f'Successfully imported {imported_count} transactions.', 'success')
            return redirect(url_for('coinbase.transactions'))
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")
            flash(f'Failed to import transactions: {str(e)}', 'error')
            return redirect(url_for('coinbase.import_transactions'))

    return render_template('import_transactions.html')