from flask import render_template, redirect, url_for, request, session, flash
from database.models import db, User
from werkzeug.security import generate_password_hash
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='log.txt')
logger = logging.getLogger(__name__)

def settings():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    return render_template('settings.html', user=user)

def update_email():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    email = request.form['email']
    if User.query.filter_by(email=email).first() and email != user.email:
        flash('Email already in use.', 'error')
    else:
        user.email = email
        db.session.commit()
        logger.info(f"User {user.username} updated email to {email}")
        flash('Email updated successfully.', 'success')

    return redirect(url_for('settings.settings'))

def update_password():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    password = request.form['password']
    user.password = generate_password_hash(password, method='pbkdf2:sha256')
    db.session.commit()
    logger.info(f"User {user.username} updated password")
    flash('Password updated successfully.', 'success')
    return redirect(url_for('settings.settings'))

def update_coinbase_credentials():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    api_key = request.form['api_key']
    api_secret = request.form['api_secret']

    try:
        user.set_coinbase_api_key(api_key)
        user.set_coinbase_api_secret(api_secret)
        db.session.commit()
        logger.info(f"User {user.username} updated Coinbase credentials")
        flash('Coinbase API credentials updated successfully.', 'success')
    except Exception as e:
        logger.error(f"Error updating Coinbase credentials for {user.username}: {str(e)}")
        flash('Failed to update Coinbase API credentials.', 'error')

    return redirect(url_for('settings.settings'))