from flask import redirect, url_for, request, session, flash, send_file
from database.models import db, User, Transaction
import pandas as pd
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='log.txt')
logger = logging.getLogger(__name__)

def export_fidelity_transactions():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('settings.settings'))

    transactions = Transaction.query.filter_by(user_id=user.id, source='fidelity').all()
    if not transactions:
        flash('No Fidelity transactions to export.', 'info')
        return redirect(url_for('settings.settings'))

    data = [{
        'ID': tx.coinbase_tx_id,
        'Run Date': tx.timestamp.isoformat(),
        'Action': tx.type,
        'Symbol': tx.currency,
        'Quantity': tx.amount,
        'Price': tx.price_at_transaction
    } for tx in transactions]

    df = pd.DataFrame(data)
    filename = f"fidelity_transactions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    logger.info(f"User {user.username} exported Fidelity transactions to {filename}")
    flash('Fidelity transactions exported successfully.', 'success')
    return send_file(filename, as_attachment=True)

def import_fidelity_transactions():
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
        required_columns = ['ID', 'Run Date', 'Action', 'Symbol', 'Quantity', 'Price']
        if not all(col in df.columns for col in required_columns):
            flash('Invalid backup CSV format.', 'error')
            return redirect(url_for('settings.settings'))

        imported_count = 0
        for index, row in df.iterrows():
            if Transaction.query.filter_by(coinbase_tx_id=row['ID']).first():
                continue
            try:
                timestamp = pd.to_datetime(row['Run Date']).to_pydatetime()
                price = float(row['Price']) if row['Price'] else None
                amount = float(row['Quantity'])
                if row['Action'].lower() == 'sell' and amount > 0:
                    amount = -amount
                new_tx = Transaction(
                    coinbase_tx_id=row['ID'],
                    user_id=user.id,
                    type=row['Action'],
                    amount=amount,
                    currency=row['Symbol'],
                    timestamp=timestamp,
                    status='completed',
                    price_at_transaction=price,
                    source='fidelity'
                )
                db.session.add(new_tx)
                imported_count += 1
            except Exception as e:
                logger.error(f"Error importing Fidelity transaction at row {index}: {str(e)}")
                continue

        db.session.commit()
        logger.info(f"User {user.username} imported {imported_count} Fidelity transactions")
        flash(f'Successfully imported {imported_count} Fidelity transactions.', 'success')
    except Exception as e:
        logger.error(f"Error importing Fidelity backup: {str(e)}")
        flash(f'Failed to import Fidelity transactions: {str(e)}', 'error')

    return redirect(url_for('settings.settings'))

def clear_fidelity_transactions():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('settings.settings'))

    Transaction.query.filter_by(user_id=user.id, source='fidelity').delete()
    db.session.commit()
    logger.info(f"User {user.username} cleared Fidelity transactions")
    flash('Fidelity transactions cleared successfully.', 'success')
    return redirect(url_for('settings.settings'))