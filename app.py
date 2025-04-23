from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure random key
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Bind SQLAlchemy to the app
    db.init_app(app)

    # Create database within app context
    with app.app_context():
        db.create_all()

    @app.route('/')
    def home():
        if 'username' in session:
            return render_template('index.html', username=session['username'])
        return redirect(url_for('login'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            # Check if username exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists.', 'error')
                return render_template('register.html')
            
            # Hash password and create new user
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, password=hashed_password)
            
            try:
                db.session.add(new_user)
                db.session.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred during registration.', 'error')
            
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            # Find user
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password, password):
                session['username'] = username
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password.', 'error')
        
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.pop('username', None)
        flash('You have been logged out.', 'success')
        return redirect(url_for('login'))

    return app