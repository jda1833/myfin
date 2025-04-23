from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.models import db, User
import pyotp
import qrcode
import io
import base64
from PIL import Image

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        enable_2fa = 'enable_2fa' in request.form

        # Check if username exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'error')
            return render_template('register.html')

        # Hash password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Generate TOTP secret if 2FA is enabled
        totp_secret = pyotp.random_base32() if enable_2fa else None
        new_user = User(username=username, password=hashed_password, totp_secret=totp_secret)

        try:
            db.session.add(new_user)
            db.session.commit()

            if enable_2fa:
                session['setup_username'] = username
                return redirect(url_for('auth.setup_2fa'))
            else:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration.', 'error')

    return render_template('register.html')

@auth_bp.route('/setup_2fa')
def setup_2fa():
    if 'setup_username' not in session:
        return redirect(url_for('auth.register'))

    username = session['setup_username']
    user = User.query.filter_by(username=username).first()
    if not user or not user.totp_secret:
        flash('2FA setup failed.', 'error')
        return redirect(url_for('auth.login'))

    # Generate TOTP provisioning URI
    totp_uri = pyotp.totp.TOTP(user.totp_secret).provisioning_uri(
        name=username, issuer_name='FlaskApp'
    )

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    # Convert QR code to base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return render_template('2fa_setup.html', qr_code=img_str, totp_secret=user.totp_secret)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Find user
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['temp_username'] = username
            if user.totp_secret:
                return redirect(url_for('auth.verify_2fa'))
            else:
                session['username'] = username
                flash('Login successful!', 'success')
                return redirect(url_for('main.home'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')

@auth_bp.route('/verify_2fa', methods=['GET', 'POST'])
def verify_2fa():
    if 'temp_username' not in session:
        return redirect(url_for('auth.login'))

    username = session['temp_username']
    user = User.query.filter_by(username=username).first()

    if not user or not user.totp_secret:
        flash('2FA verification failed.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        totp_code = request.form['totp_code']
        totp = pyotp.TOTP(user.totp_secret)

        if totp.verify(totp_code):
            session.pop('temp_username', None)
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('main.home'))
        else:
            flash('Invalid 2FA code.', 'error')

    return render_template('2fa_verify.html')

@auth_bp.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('temp_username', None)
    session.pop('setup_username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))