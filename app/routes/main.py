from flask import Blueprint, render_template, redirect, url_for, session
from database.models import db, User

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('auth.login'))