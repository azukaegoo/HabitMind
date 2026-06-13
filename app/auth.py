import sys
from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from flask_login import login_user, logout_user, current_user 
from .models import db, User
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from . import mail

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
# CHANGE PASSWORD (From Settings)
# ═══════════════════════════════════════════
@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
        
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    
    if not current_user.check_password(old_password):
        flash('Incorrect current password.', 'error')
        return redirect(url_for('main.settings'))
        
    current_user.set_password(new_password)
    db.session.commit()
    
    logout_user()
    flash('Password changed successfully. Please log in again with your new password.', 'success')
    return redirect(url_for('auth.login'))

# ═══════════════════════════════════════════
# PASSWORD RESET LOGIC (Forgot Password)
# ═══════════════════════════════════════════
def get_reset_token(user, expires_sec=1800):
    """Generate a 30-minute security token for password reset"""
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps({'user_id': user.id})

def verify_reset_token(token, expires_sec=1800):
    """Verify the token's validity and check if it has expired"""
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        user_id = s.loads(token, max_age=expires_sec)['user_id']
    except:
        return None
    return db.session.get(User, user_id)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request a password reset link via email"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = get_reset_token(user)
            msg = Message('HabitMind Password Reset Request',
                          sender='habitmind.team@gmail.com',
                          recipients=[user.email])
            
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            msg.body = f"To reset your password, visit the following link:\n{reset_url}\n\nIf you did not make this request, simply ignore this email and no changes will be made."
            
            try:
                mail.send(msg)
                print(f"DEBUG: Reset email sent to {user.email}")
            except Exception as e:
                print(f"DEBUG: Mail Error - {e}")
                
        flash('If an account with that email exists, a reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password using the token received via email"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    user = verify_reset_token(token)
    if not user:
        flash('That is an invalid or expired token.', 'error')
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        user.set_password(password)
        db.session.commit()
        flash('Your password has been updated! You are now able to log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('reset_password.html', token=token)