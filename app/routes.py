from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from . import db
import logging
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)
main = Blueprint("main", __name__)

@main.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main.route("/dashboard")
@login_required
def dashboard():
    return render_template("home.html")

@main.route("/goals", methods=['GET', 'POST'])
@login_required
def goals():
    if request.method == 'POST':
        selected_goals = request.form.get('goals')
        
        current_user.selected_goals = selected_goals
        db.session.commit()
        
        print(f"DEBUG: Saved goals for {current_user.email} -> {selected_goals}", flush=True)
        return redirect(url_for('main.dashboard'))
        
    return render_template("goals.html")