from flask import render_template, redirect, url_for, request, session, flash
from database.models import db, User
import pyotp
import qrcode
from io import BytesIO
import base64
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='log.txt')
logger = logging.getLogger(__name__)

def setup_2fa():
    if 'username' not in session:
        flash('Please log in to set up 2FA', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.login'))

    if user.totp_secret:
        flash('2FA is already enabled', 'info')
        return redirect(url_for('settings.settings'))

    # Generate TOTP secret
    secret = pyotp.random_base32()
    session['totp_secret'] = secret

    # Generate provisioning URI for QR code
    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.username,
        issuer_name='CryptoApp'
    )

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert QR code to base64 for embedding in HTML
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return render_template('2fa_setup.html', qr_base64=qr_base64, secret=secret)

def verify_2fa():
    if 'username' not in session and 'username_pending' not in session:
        flash('Please log in to verify 2FA', 'error')
        return redirect(url_for('auth.login'))

    username = session.get('username') or session.get('username_pending')
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form['code']
        secret = session.get('totp_secret') if 'username' in session else user.totp_secret

        if not secret:
            flash('No 2FA setup in progress', 'error')
            return redirect(url_for('auth.login'))

        totp = pyotp.TOTP(secret)
        if totp.verify(code):
            if 'username' in session:
                # Setting up 2FA
                user.totp_secret = secret
                db.session.commit()
                session.pop('totp_secret', None)
                logger.info(f"User {username} enabled 2FA")
                flash('2FA enabled successfully', 'success')
                return redirect(url_for('settings.settings'))
            else:
                # Logging in with 2FA
                session.pop('username_pending', None)
                session['username'] = username
                logger.info(f"User {username} logged in with 2FA")
                return redirect(url_for('main.index'))
        else:
            flash('Invalid 2FA code', 'error')

    return render_template('2fa_verify.html')

def disable_2fa():
    if 'username' not in session:
        flash('Please log in to disable 2FA', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.login'))

    if user.totp_secret:
        user.totp_secret = None
        db.session.commit()
        logger.info(f"User {user.username} disabled 2FA")
        flash('2FA disabled successfully', 'success')
    else:
        flash('2FA is not enabled', 'info')

    return redirect(url_for('settings.settings'))