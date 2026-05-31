from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from . import db
from .models import CheckIn  
import logging
from flask_login import login_required, current_user
from datetime import datetime, UTC

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

@main.route("/checkin", methods=['POST'])
@login_required
def checkin():
    mood_score = request.form.get('mood_score') 
    habits = request.form.get('habits')         
    note = request.form.get('note')             
    
    if not mood_score:
        flash('Mood score is required!')
        return redirect(url_for('main.dashboard'))
        
    try:
        mood_score = int(mood_score)
    except ValueError:
        flash('Invalid mood score format!')
        return redirect(url_for('main.dashboard'))
        
    today = datetime.now(UTC).date()
    
    # Task: Check whether the user already submitted today's check-in
    existing_checkin = CheckIn.query.filter_by(user_id=current_user.id, date=today).first()
    
    if existing_checkin:
        # Goal: Prevent duplicate daily check-ins by blocking the submission
        flash('You have already submitted your check-in for today!')
        print(f"DEBUG: Blocked duplicate check-in attempt for {current_user.email}", flush=True)
        return redirect(url_for('main.dashboard'))
    
    # If no existing check-in, create a new one
    new_checkin = CheckIn(
        user_id=current_user.id,
        mood_score=mood_score,
        habits=habits,
        note=note,
        date=today
    )
    db.session.add(new_checkin)
    print(f"DEBUG: Created new daily check-in for {current_user.email}", flush=True)
    
    db.session.commit()
    flash('Daily check-in saved successfully!')
    return redirect(url_for('main.dashboard'))