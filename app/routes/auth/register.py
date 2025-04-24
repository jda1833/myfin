from flask import render_template, redirect, url_for, request, session, flash
from database.models import db, User
from werkzeug.security import generate_password_hash
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='log.txt')
logger = logging.getLogger(__name__)

def register():
    if 'username' in session:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            logger.info(f"User {username} registered")
            session['username'] = username
            return redirect(url_for('main.index'))

    return render_template('register.html')