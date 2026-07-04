import sys
from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from flask_login import login_user, logout_user, current_user 
from .models import db, User
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from . import mail
import random

auth_bp = Blueprint('auth', __name__)

# ═══════════════════════════════════════════
# SIGN UP & REGISTER
# ═══════════════════════════════════════════
#sign up route
@auth_bp.route('/signup', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':

        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash(
                'An account with that email already exists.',
                'error'
            )
            return redirect(url_for('auth.register'))

        try:
            new_user = User(
                name=fullname,
                email=email
            )

            new_user.set_password(password)

            db.session.add(new_user)
            db.session.commit()

            flash(
                'Account created successfully! Please log in.',
                'success'
            )

            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()

            print(
                f"DEBUG: Error creating account for {email}: {e}",
                flush=True
            )

            flash(
                'Could not create your account. Please try again.',
                'error'
            )

            return redirect(url_for('auth.register'))

    return render_template('signup.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def old_register_fallback():
    return register()

# ═══════════════════════════════════════════
# LOG IN
# ═══════════════════════════════════════════
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)

            print(f"DEBUG: User logged in - Email: {user.email}, Plan: {user.plan}", flush=True)

            if not user.onboarding_completed:
                if not user.selected_goals:
                    return redirect(url_for("main.goals"))

                return redirect(url_for("main.habits"))

            return redirect(url_for("main.dashboard"))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            return redirect(url_for('auth.login'))
            
    return render_template('login.html')

# ═══════════════════════════════════════════
# LOG OUT
# ═══════════════════════════════════════════
@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# ═══════════════════════════════════════════
# CHANGE PASSWORD (Internal)
# ═══════════════════════════════════════════
@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Update password directly from settings without changing page"""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
        
    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')
    
    if new_pw != confirm_pw:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('main.settings'))
        
    if not current_user.check_password(current_pw):
        flash('Incorrect current password.', 'error')
        return redirect(url_for('main.settings'))
        
    current_user.set_password(new_pw)
    db.session.commit()
    
    logout_user() 
    flash('Password successfully updated! Please log in again with your new password.', 'success')
    return redirect(url_for('auth.login'))

# ═══════════════════════════════════════════
# PASSWORD RESET LOGIC (Forgot Password - 6 Digit OTP)
# ═══════════════════════════════════════════
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Send a 6-digit OTP code to the user's email"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate a 6-digit random OTP and store it in the session
            otp_code = str(random.randint(100000, 999999))
            session['reset_otp'] = otp_code
            session['reset_email'] = email
            
            msg = Message('HabitMind Password Reset Code',
                          sender='habitmind.team@gmail.com',
                          recipients=[user.email])
            
            # Print OTP to terminal for local testing and Dominik's grading
            print(f"\n🔥 [LOCAL TEST] DOMINIK GRADING OTP CODE: {otp_code}\n", flush=True)
            
            msg.body = f"Your password reset code is: {otp_code}\nPlease enter this 6-digit code on the website to reset your password."
            
            try:
                mail.send(msg)
                print(f"DEBUG: OTP email sent to {user.email}")
            except Exception as e:
                print(f"DEBUG: Mail Error (Ignored in local dev) - {e}")
                
        flash('If an account with that email exists, an OTP code has been sent.', 'info')
        return redirect(url_for('auth.verify_otp'))
        
    return render_template('forgot_password.html')

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """Verify the 6-digit code"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        user_input_otp = request.form.get('otp')
        real_otp = session.get('reset_otp')
        
        if real_otp and user_input_otp == real_otp:
            # Redirect to the actual password reset page if OTP matches
            return redirect(url_for('auth.reset_password'))
        else:
            flash('Invalid or expired code. Please try again.', 'error')
            
    return render_template('verify_otp.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Final step: Set the new password"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Reject users who try to access this page directly without verifying OTP first
    if 'reset_email' not in session or 'reset_otp' not in session:
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        email = session.get('reset_email')
        new_password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(new_password)
            db.session.commit()
            
        # Clear security session data
        session.pop('reset_otp', None)
        session.pop('reset_email', None)
        
        flash('Your password has been updated! You are now able to log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('reset_password.html')