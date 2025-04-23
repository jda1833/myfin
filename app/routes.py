# app/routes.py
# Defines routes for registration, login, 2FA, API key input, and transaction display.
# python
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, current_app
import bcrypt
import pyotp
import qrcode
import io
import base64
import pandas as pd
from coinbase.wallet.client import Client
from .models import User

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    return render_template('index.html', username=session['username'])

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        print(request)
        db_session = current_app.config['DB_SESSION']
        existing_user = db_session.query(User).filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!')
            return redirect(url_for('main.register'))
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        totp_secret = pyotp.random_base32()
        
        new_user = User(
            username=username,
            password=hashed_password.decode('utf-8'),
            email=email,
            totp_secret=totp_secret
        )
        db_session.add(new_user)
        db_session.commit()
        
        totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
            name=username,
            issuer_name='CoinbaseTracker'
        )
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        session['temp_user_id'] = new_user.id
        session['qr_base64'] = qr_base64
        return redirect(url_for('main.show_qr'))
    
    return render_template('register.html')

@bp.route('/show_qr')
def show_qr():
    if 'qr_base64' not in session:
        flash('Please register first!')
        return redirect(url_for('main.register'))
    qr_base64 = session['qr_base64']
    return render_template('show_qr.html', qr_base64=qr_base64)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db_session = current_app.config['DB_SESSION']
        user = db_session.query(User).filter_by(username=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            session['temp_user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('main.verify_2fa'))
        else:
            flash('Invalid username or password!')
    
    return render_template('login.html')

@bp.route('/verify_2fa', methods=['GET', 'POST'])
def verify_2fa():
    if 'temp_user_id' not in session:
        flash('Please log in first!')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        code = request.form['code']
        db_session = current_app.config['DB_SESSION']
        user = db_session.query(User).filter_by(id=session['temp_user_id']).first()
        totp = pyotp.TOTP(user.totp_secret)
        
        if totp.verify(code):
            session['user_id'] = user.id
            session.pop('temp_user_id', None)
            session.pop('qr_base64', None)
            flash('Login successful!')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid 2FA code!')
    
    return render_template('verify_2fa.html')

@bp.route('/api_keys', methods=['GET', 'POST'])
def api_keys():
    if 'user_id' not in session:
        flash('Please log in first!')
        return redirect(url_for('main.login'))
    
    db_session = current_app.config['DB_SESSION']
    user = db_session.query(User).filter_by(id=session['user_id']).first()
    
    if request.method == 'POST':
        api_key = request.form['api_key']
        api_secret = request.form['api_secret']
        user.set_api_keys(api_key, api_secret)
        db_session.commit()
        flash('Coinbase API keys saved successfully!')
        return redirect(url_for('main.index'))
    
    return render_template('api_keys.html')

@bp.route('/transactions')
def transactions():
    if 'user_id' not in session:
        flash('Please log in first!')
        return redirect(url_for('main.login'))
    
    db_session = current_app.config['DB_SESSION']
    user = db_session.query(User).filter_by(id=session['user_id']).first()
    api_key, api_secret = user.get_api_keys()
    
    if not api_key or not api_secret:
        flash('Please set your Coinbase API keys first!')
        return redirect(url_for('main.api_keys'))
    
    try:
        client = Client(api_key, api_secret)
        accounts = client.get_accounts()['data']
        transactions = []
        for account in accounts:
            txs = client.get_transactions(account['id'])['data']
            for tx in txs:
                transactions.append({
                    'id': tx['id'],
                    'type': tx['type'],
                    'amount': tx['amount']['amount'],
                    'currency': tx['amount']['currency'],
                    'created_at': tx['created_at'],
                    'status': tx['status']
                })
        
        df = pd.DataFrame(transactions)
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        return render_template('transactions.html', tables=[df.to_html(classes='table', index=False)], titles=['Coinbase Transactions'])
    except Exception as e:
        flash(f'Error fetching transactions: {str(e)}')
        return redirect(url_for('main.index'))

@bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!')
    return redirect(url_for('main.login'))
