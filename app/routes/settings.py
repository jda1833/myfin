from flask import Blueprint, render_template, redirect, url_for, session, flash, request, jsonify
from database.models import db, User, Transaction
from werkzeug.security import check_password_hash, generate_password_hash
import logging

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