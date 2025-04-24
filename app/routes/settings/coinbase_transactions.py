from flask import redirect, url_for, request, session, flash, send_file
from database.models import db, User, Transaction
import pandas as pd
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='log.txt')
logger = logging.getLogger(__name__)

def export_transactions():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('settings.settings'))

    transactions = Transaction.query.filter_by(user_id=user.id, source='coinbase').all()
    if not transactions:
        flash('No Coinbase transactions to export.', 'info')
        return redirect(url_for('settings.settings'))

    data = [{
        'ID': tx.coinbase_tx_id,
        'Timestamp': tx.timestamp.isoformat(),
        'Transaction Type': tx.type,
        'Asset': tx.currency,
        'Quantity Transacted': tx.amount,
        'Price at Transaction': tx.price_at_transaction,
        'Notes': ''
    } for tx in transactions]

    df = pd.DataFrame(data)
    filename = f"coinbase_transactions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    logger.info(f"User {user.username} exported Coinbase transactions to {filename}")
    flash('Coinbase transactions exported successfully.', 'success')
    return send_file(filename, as_attachment=True)

def import_transactions():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('settings.settings'))

    if 'backup_file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('settings.settings'))

    file = request.files['backup_file']
    if not file or not file.filename.endswith('.csv'):
        flash('Please upload a valid CSV file.', 'error')
        return redirect(url_for('settings.settings'))

    try:
        df = pd.read_csv(file)
        required_columns = ['ID', 'Timestamp', 'Transaction Type', 'Asset', 'Quantity Transacted', 'Price at Transaction']
        if not all(col in df.columns for col in required_columns):
            flash('Invalid backup CSV format.', 'error')
            return redirect(url_for('settings.settings'))

        imported_count = 0
        for index, row in df.iterrows():
            if Transaction.query.filter_by(coinbase_tx_id=row['ID']).first():
                continue
            try:
                timestamp = pd.to_datetime(row['Timestamp']).to_pydatetime()
                price = float(row['Price at Transaction']) if row['Price at Transaction'] else None
                new_tx = Transaction(
                    coinbase_tx_id=row['ID'],
                    user_id=user.id,
                    type=row['Transaction Type'],
                    amount=float(row['Quantity Transacted']),
                    currency=row['Asset'],
                    timestamp=timestamp,
                    status='completed',
                    price_at_transaction=price,
                    source='coinbase'
                )
                db.session.add(new_tx)
                imported_count += 1
            except Exception as e:
                logger.error(f"Error importing Coinbase transaction at row {index}: {str(e)}")
                continue

        db.session.commit()
        logger.info(f"User {user.username} imported {imported_count} Coinbase transactions")
        flash(f'Successfully imported {imported_count} Coinbase transactions.', 'success')
    except Exception as e:
        logger.error(f"Error importing Coinbase backup: {str(e)}")
        flash(f'Failed to import Coinbase transactions: {str(e)}', 'error')

    return redirect(url_for('settings.settings'))

def clear_transactions():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('settings.settings'))

    Transaction.query.filter_by(user_id=user.id, source='coinbase').delete()
    db.session.commit()
    logger.info(f"User {user.username} cleared Coinbase transactions")
    flash('Coinbase transactions cleared successfully.', 'success')
    return redirect(url_for('settings.settings'))