from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.models import db, User
import pyotp

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
        # Coinbase API credentials
        coinbase_api_key = request.form.get('coinbase_api_key')
        coinbase_api_secret = request.form.get('coinbase_api_secret')
        if coinbase_api_key and coinbase_api_secret:
            user.set_coinbase_api_key(coinbase_api_key)
            user.set_coinbase_api_secret(coinbase_api_secret)
            flash('Coinbase API credentials updated.', 'success')
        elif coinbase_api_key or coinbase_api_secret:
            flash('Both API key and secret must be provided.', 'error')
            return redirect(url_for('settings.settings'))

        # Email
        email = request.form.get('email')
        if email:
            if User.query.filter_by(email=email).first() and user.email != email:
                flash('Email already in use.', 'error')
                return redirect(url_for('settings.settings'))
            user.email = email
            flash('Email updated.', 'success')

        # 2FA
        enable_2fa = 'enable_2fa' in request.form
        if enable_2fa and not user.totp_secret:
            user.totp_secret = pyotp.random_base32()
            db.session.commit()
            session['setup_username'] = user.username
            return redirect(url_for('auth.setup_2fa'))
        elif not enable_2fa and user.totp_secret:
            user.totp_secret = None
            flash('2FA disabled.', 'success')

        # Password
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if current_password and new_password and confirm_password:
            if not check_password_hash(user.password, current_password):
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('settings.settings'))
            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                return redirect(url_for('settings.settings'))
            user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            flash('Password updated.', 'success')

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while saving settings.', 'error')

        return redirect(url_for('settings.settings'))

    return render_template('settings.html', user=user)