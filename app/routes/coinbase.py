from flask import Blueprint, render_template, redirect, url_for, session, flash, request
from database.models import db, User, Transaction
from coinbase.wallet.client import Client
from datetime import datetime
import pandas as pd
import logging
from sqlalchemy import func

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='log.txt')
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
    query = Transaction.query.filter_by(user_id=user.id, source='coinbase')

    # Apply currency filter
    if currency:
        query = query.filter_by(currency=currency)

    # Paginate results
    pagination = query.order_by(Transaction.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items

    # Get unique currencies for filter dropdown
    currencies = db.session.query(Transaction.currency).filter_by(user_id=user.id, source='coinbase').distinct().all()
    currencies = [c[0] for c in currencies]

    # Prepare chart data (cumulative amount owned by date)
    chart_query = Transaction.query.filter_by(user_id=user.id, source='coinbase')
    if currency:
        chart_query = chart_query.filter_by(currency=currency)

    chart_transactions = (
        chart_query
        .filter(Transaction.status == 'completed')
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
        if tx.type.lower() in ['sell', 'send']:
            amount = -amount
        balance += amount
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

@coinbase_bp.route('/fetch_transactions')
def fetch_transactions():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    if not user.coinbase_api_key or not user.coinbase_api_secret:
        flash('Coinbase API credentials not set.', 'error')
        return redirect(url_for('settings.settings'))

    try:
        client = Client(user.get_coinbase_api_key(), user.get_coinbase_api_secret())
        accounts = client.get_accounts()['data']
        imported_count = 0

        for account in accounts:
            transactions = client.get_transactions(account['id'])['data']
            for tx in transactions:
                tx_id = tx['id']
                if Transaction.query.filter_by(coinbase_tx_id=tx_id).first():
                    continue

                try:
                    amount = float(tx['amount']['amount'])
                    currency = tx['amount']['currency']
                    timestamp = datetime.strptime(tx['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    status = tx['status']
                    tx_type = tx['type']
                    price = None

                    if tx_type.lower() in ['sell', 'send']:
                        amount = -amount

                    new_tx = Transaction(
                        coinbase_tx_id=tx_id,
                        user_id=user.id,
                        type=tx_type,
                        amount=amount,
                        currency=currency,
                        timestamp=timestamp,
                        status=status,
                        price_at_transaction=price,
                        source='coinbase'
                    )
                    db.session.add(new_tx)
                    imported_count += 1
                except Exception as e:
                    logger.error(f"Error processing Coinbase transaction {tx_id}: {str(e)}")
                    continue

        db.session.commit()
        flash(f'Successfully imported {imported_count} transactions from Coinbase.', 'success')
    except Exception as e:
        logger.error(f"Error fetching Coinbase transactions: {str(e)}")
        flash(f'Failed to fetch transactions: {str(e)}', 'error')

    return redirect(url_for('coinbase.transactions'))

@coinbase_bp.route('/import_transactions', methods=['GET', 'POST'])
def import_transactions():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('coinbase.import_transactions'))

        file = request.files['csv_file']
        if not file or not file.filename.endswith('.csv'):
            flash('Please upload a valid CSV file.', 'error')
            return redirect(url_for('coinbase.import_transactions'))

        try:
            df = pd.read_csv(file)
            logger.debug(f"CSV columns: {df.columns.tolist()}")

            required_columns = ['ID', 'Timestamp', 'Transaction Type', 'Asset', 'Quantity Transacted', 'Price at Transaction']
            if not all(col in df.columns for col in required_columns):
                flash('Invalid CSV format. Ensure it includes Timestamp, Transaction Type, Asset, Quantity Transacted, and Price at Transaction.', 'error')
                return redirect(url_for('coinbase.import_transactions'))

            imported_count = 0
            for index, row in df.iterrows():
                tx_id = row['ID']
                if Transaction.query.filter_by(coinbase_tx_id=tx_id).first():
                    continue

                try:
                    timestamp = pd.to_datetime(row['Timestamp']).to_pydatetime()
                    tx_type = row['Transaction Type']
                    amount = float(row['Quantity Transacted'])
                    if tx_type.lower() in ['sell', 'send']:
                        amount = -amount
                    if tx_type.lower() == 'convert':
                        # For Convert, split into two transactions: sell and buy
                        convert_from_qty = float(row['Quantity Transacted'])
                        convert_from_asset = row['Asset']
                        convert_to_qty = float(row['Total (inclusive of fees)'])
                        convert_to_asset = row['Notes'].split(' to ')[1].split()[0]

                        # Sell transaction
                        sell_tx = Transaction(
                            coinbase_tx_id=f"{tx_id}_sell",
                            user_id=user.id,
                            type='sell',
                            amount=-convert_from_qty,
                            currency=convert_from_asset,
                            timestamp=timestamp,
                            status='completed',
                            price_at_transaction=None,
                            source='coinbase'
                        )
                        db.session.add(sell_tx)

                        # Buy transaction
                        buy_tx = Transaction(
                            coinbase_tx_id=f"{tx_id}_buy",
                            user_id=user.id,
                            type='buy',
                            amount=convert_to_qty,
                            currency=convert_to_asset,
                            timestamp=timestamp,
                            status='completed',
                            price_at_transaction=None,
                            source='coinbase'
                        )
                        db.session.add(buy_tx)
                        imported_count += 2
                        continue

                    price = float(row['Price at Transaction'].replace('$', '').replace(',', '').strip()) if row['Price at Transaction'] and str(row['Price at Transaction']).replace('$', '').replace(',', '').strip() else None
                    new_tx = Transaction(
                        coinbase_tx_id=tx_id,
                        user_id=user.id,
                        type=tx_type,
                        amount=amount,
                        currency=row['Asset'],
                        timestamp=timestamp,
                        status='completed',
                        price_at_transaction=price,
                        source='coinbase'
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