import sys
from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from flask_login import login_user, logout_user, current_user 
from .models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already exists.')
            return redirect(url_for('auth.old_register_fallback'))
            
        # Create and save new user
        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        # Auto-login and redirect to onboarding
        login_user(new_user)
        return redirect(url_for('main.goals'))
        
    return render_template('signup.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def old_register_fallback():
    return register()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            
            print(f"DEBUG: User logged in - Email: {user.email}, Plan: {user.plan}", flush=True)
            print(f"DEBUG: Is user premium? -> {user.is_premium()}", flush=True)
            
            # If onboarding is not complete, redirect to goals
            if not user.selected_goals:
                return redirect(url_for('main.goals'))
            
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password.')
            
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))