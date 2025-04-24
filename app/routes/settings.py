from flask import Blueprint, render_template, redirect, url_for, session, flash, request, jsonify, Response
from database.models import db, User, Transaction
from werkzeug.security import check_password_hash, generate_password_hash
import logging
import pandas as pd
from io import StringIO
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # Update Email
        if form_type == 'update_email':
            email = request.form.get('email')
            if email:
                user.email = email
                session['email'] = email
                db.session.commit()
                flash('Email updated successfully.', 'success')
            else:
                flash('Email cannot be empty.', 'error')

        # Update Password
        elif form_type == 'update_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not check_password_hash(user.password, current_password):
                flash('Current password is incorrect.', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'error')
            elif len(new_password) < 8:
                flash('New password must be at least 8 characters.', 'error')
            else:
                user.password = generate_password_hash(new_password)
                db.session.commit()
                flash('Password updated successfully.', 'success')

        # Update Coinbase API Credentials
        elif form_type == 'update_credentials':
            api_key = request.form.get('coinbase_api_key')
            api_secret = request.form.get('coinbase_api_secret')
            try:
                user.set_coinbase_api_key(api_key)
                user.set_coinbase_api_secret(api_secret)
                db.session.commit()
                session['coinbase_api_key'] = api_key
                session['coinbase_api_secret'] = api_secret
                flash('Coinbase API credentials updated successfully.', 'success')
            except Exception as e:
                logger.error(f"Error updating Coinbase credentials: {str(e)}")
                flash('Failed to update Coinbase API credentials.', 'error')

        return redirect(url_for('settings.settings'))

    return render_template('settings.html', user=user)

@settings_bp.route('/clear_transactions', methods=['POST'])
def clear_transactions():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Please log in.'}), 401

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404

    # Verify CSRF token
    csrf_token = request.headers.get('X-CSRF-Token')
    if not csrf_token or csrf_token != session.get('csrf_token'):
        logger.warning(f"CSRF token validation failed for user {session['username']}")
        return jsonify({'success': False, 'message': 'Invalid CSRF token.'}), 403

    try:
        # Delete all transactions for the user
        num_deleted = db.session.query(Transaction).filter_by(user_id=user.id).delete()
        db.session.commit()
        logger.info(f"User {session['username']} cleared {num_deleted} transactions")
        return jsonify({'success': True, 'message': f'Successfully cleared {num_deleted} transactions.'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing transactions for user {session['username']}: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to clear transactions: {str(e)}'}), 500

@settings_bp.route('/export_transactions', methods=['GET'])
def export_transactions():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Please log in.'}), 401

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404

    # Verify CSRF token
    csrf_token = request.headers.get('X-CSRF-Token')
    if not csrf_token or csrf_token != session.get('csrf_token'):
        logger.warning(f"CSRF token validation failed for user {session['username']}")
        return jsonify({'success': False, 'message': 'Invalid CSRF token.'}), 403

    try:
        # Fetch all transactions for the user
        transactions = Transaction.query.filter_by(user_id=user.id).all()
        if not transactions:
            return jsonify({'success': False, 'message': 'No transactions to export.'}), 404

        # Create CSV
        columns = ['coinbase_tx_id', 'type', 'amount', 'currency', 'timestamp', 'status', 'price_at_transaction']
        data = [{
            'coinbase_tx_id': tx.coinbase_tx_id,
            'type': tx.type,
            'amount': tx.amount,
            'currency': tx.currency,
            'timestamp': tx.timestamp.isoformat(),
            'status': tx.status,
            'price_at_transaction': tx.price_at_transaction
        } for tx in transactions]

        df = pd.DataFrame(data, columns=columns)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()

        logger.info(f"User {session['username']} exported {len(transactions)} transactions")
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename=transactions_backup_{datetime.now().strftime("%Y%m%d")}.csv'}
        )
    except Exception as e:
        logger.error(f"Error exporting transactions for user {session['username']}: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to export transactions: {str(e)}'}), 500

@settings_bp.route('/import_transactions', methods=['POST'])
def import_transactions():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Please log in.'}), 401

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404

    # Verify CSRF token
    csrf_token = request.headers.get('X-CSRF-Token')
    if not csrf_token or csrf_token != session.get('csrf_token'):
        logger.warning(f"CSRF token validation failed for user {session['username']}")
        return jsonify({'success': False, 'message': 'Invalid CSRF token.'}), 403

    # Check if a file was uploaded
    if 'csv_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file selected.'}), 400

    file = request.files['csv_file']
    if not file or not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'message': 'Please upload a valid CSV file.'}), 400

    try:
        # Read CSV
        df = pd.read_csv(file)
        logger.debug(f"Backup CSV columns: {df.columns.tolist()}")

        # Required columns
        required_columns = ['coinbase_tx_id', 'type', 'amount', 'currency', 'timestamp', 'status']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'success': False, 'message': 'Invalid CSV format. Ensure it includes coinbase_tx_id, type, amount, currency, timestamp, status.'}), 400

        # Process each row
        imported_count = 0
        for index, row in df.iterrows():
            coinbase_tx_id = row['coinbase_tx_id']
            if Transaction.query.filter_by(coinbase_tx_id=coinbase_tx_id).first():
                continue  # Skip duplicates

            try:
                timestamp = pd.to_datetime(row['timestamp']).to_pydatetime()
                price = float(row['price_at_transaction']) if pd.notnull(row.get('price_at_transaction')) else None
                new_tx = Transaction(
                    coinbase_tx_id=coinbase_tx_id,
                    user_id=user.id,
                    type=row['type'].lower(),
                    amount=float(row['amount']),
                    currency=row['currency'],
                    timestamp=timestamp,
                    status=row['status'],
                    price_at_transaction=price
                )
                db.session.add(new_tx)
                imported_count += 1
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing backup row {index}: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing backup row {index}: {str(e)}")
                continue

        db.session.commit()
        logger.info(f"User {session['username']} imported {imported_count} transactions from backup")
        return jsonify({'success': True, 'message': f'Successfully imported {imported_count} transactions.'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error importing backup for user {session['username']}: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to import transactions: {str(e)}'}), 500