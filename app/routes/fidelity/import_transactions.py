from flask import render_template, redirect, url_for, session, flash, request
from database.models import db, User, Transaction
from datetime import datetime
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='log.txt')
logger = logging.getLogger(__name__)

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
            return redirect(url_for('fidelity.import_transactions'))

        file = request.files['csv_file']
        if not file or not file.filename.endswith('.csv'):
            flash('Please upload a valid CSV file.', 'error')
            return redirect(url_for('fidelity.import_transactions'))

        try:
            df = pd.read_csv(file)
            logger.debug(f"Fidelity CSV columns: {df.columns.tolist()}")

            # Required Fidelity CSV columns
            required_columns = ['Run Date', 'Action', 'Symbol', 'Quantity', 'Price']
            if not all(col in df.columns for col in required_columns):
                flash('Invalid CSV format. Ensure it includes Run Date, Action, Symbol, Quantity, and Price.', 'error')
                return redirect(url_for('fidelity.import_transactions'))

            imported_count = 0
            for index, row in df.iterrows():
                tx_id = f"fidelity_{index}_{row['Run Date']}_{row['Symbol']}"
                if Transaction.query.filter_by(coinbase_tx_id=tx_id).first():
                    continue

                try:
                    timestamp = pd.to_datetime(row['Run Date']).to_pydatetime()
                    tx_type = row['Action']
                    amount = float(row['Quantity'])
                    if tx_type.lower() == 'sell' and amount > 0:
                        amount = -amount
                    price = float(row['Price']) if row['Price'] and str(row['Price']).replace('$', '').strip() else None
                    new_tx = Transaction(
                        coinbase_tx_id=tx_id,
                        user_id=user.id,
                        type=tx_type,
                        amount=amount,
                        currency=row['Symbol'],
                        timestamp=timestamp,
                        status='completed',
                        price_at_transaction=price,
                        source='fidelity'
                    )
                    db.session.add(new_tx)
                    imported_count += 1
                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing Fidelity row {index}: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error processing Fidelity row {index}: {str(e)}")
                    continue

            db.session.commit()
            flash(f'Successfully imported {imported_count} Fidelity transactions.', 'success')
            return redirect(url_for('fidelity.transactions'))
        except Exception as e:
            logger.error(f"Error processing Fidelity CSV: {str(e)}")
            flash(f'Failed to import transactions: {str(e)}', 'error')
            return redirect(url_for('fidelity.import_transactions'))

    return render_template('fidelity_import_transactions.html')