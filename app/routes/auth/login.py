from flask import render_template, redirect, url_for, request, session, flash
from database.models import db, User
from werkzeug.security import check_password_hash
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='log.txt')
logger = logging.getLogger(__name__)

def login():
    if 'username' in session:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            if user.totp_secret:
                session['username_pending'] = username
                return redirect(url_for('auth.verify_2fa'))
            session['username'] = username
            logger.info(f"User {username} logged in")
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

def logout():
    username = session.pop('username', None)
    session.pop('username_pending', None)
    if username:
        logger.info(f"User {username} logged out")
    return redirect(url_for('auth.login'))