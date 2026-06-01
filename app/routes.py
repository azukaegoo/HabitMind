from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from . import db
from .models import CheckIn  
import logging
from flask_login import login_required, current_user
from datetime import datetime, UTC, timedelta
from sqlalchemy import func
from itertools import combinations
from collections import Counter

logger = logging.getLogger(__name__)
main = Blueprint("main", __name__)

def premium_required(f):
    """Decorator to require premium plan for specific routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.plan != 'premium':
            flash('This feature is for Premium users only!')
            print(f"DEBUG: Blocked free user {current_user.email} from premium feature", flush=True)
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@main.route("/")
def home():
    """Redirect to dashboard if logged in, otherwise to login page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main.route("/dashboard")
@login_required
def dashboard():
    """Render the dashboard with aggregated user statistics."""
    user_id = current_user.id
    today = datetime.now(UTC).date()
    
    # 1. Calculate Today's Check-in Status
    today_checkin = CheckIn.query.filter_by(user_id=user_id, date=today).first()
    has_checked_in_today = today_checkin is not None
    
    # 2. Calculate Total Check-ins
    total_checkins = CheckIn.query.filter_by(user_id=user_id).count()
    
    # 3. Calculate Average Mood Score
    avg_mood_result = db.session.query(func.avg(CheckIn.mood_score)).filter_by(user_id=user_id).scalar()
    average_mood = round(avg_mood_result, 1) if avg_mood_result else 0.0
    
    # 4. Calculate Current Streak (Consecutive days)
    checkins = CheckIn.query.filter_by(user_id=user_id).order_by(CheckIn.date.desc()).all()
    
    current_streak = 0
    if checkins:
        first_date = checkins[0].date
        if first_date == today or first_date == today - timedelta(days=1):
            current_streak = 1
            expected_date = first_date - timedelta(days=1)
            for i in range(1, len(checkins)):
                if checkins[i].date == expected_date:
                    current_streak += 1
                    expected_date -= timedelta(days=1)
                else:
                    break

    # 5. Calculate Habit-Mood Insights
    all_checkins = CheckIn.query.filter_by(user_id=user_id).all()
    habit_stats = {}
    
    for checkin in all_checkins:
        if checkin.habits:
            habits_list = [h.strip() for h in checkin.habits.split(',') if h.strip()]
            for habit in habits_list:
                if habit not in habit_stats:
                    habit_stats[habit] = {"total_mood": 0, "count": 0}
                habit_stats[habit]["total_mood"] += checkin.mood_score
                habit_stats[habit]["count"] += 1
                
    ranked_habits = []
    for habit, stats in habit_stats.items():
        avg = stats["total_mood"] / stats["count"]
        ranked_habits.append({"habit": habit, "average_mood": round(avg, 2)})
        
    ranked_habits.sort(key=lambda x: x["average_mood"], reverse=True)

    # 6. Find Common Habit Combinations on High-Mood Days (Mood >= 4)
    # Goal: Identify which habits frequently appear together when the user is happy
    habit_pairs = []
    for checkin in all_checkins:
        if checkin.mood_score >= 4 and checkin.habits:
            # Clean and sort so ('A', 'B') is treated the same as ('B', 'A')
            habits_list = sorted([h.strip() for h in checkin.habits.split(',') if h.strip()])
            if len(habits_list) >= 2:
                # Generate all possible pairs of habits from this check-in
                pairs = list(combinations(habits_list, 2))
                habit_pairs.extend(pairs)
                
    # Count the frequencies of each pair and get the top 3
    pair_counts = Counter(habit_pairs)
    top_combinations = [{"pair": " + ".join(pair), "count": count} for pair, count in pair_counts.most_common(3)]
                    
    print(f"DEBUG: Dashboard stats for {current_user.email} -> Streak: {current_streak}, Top Combo: {top_combinations[0]['pair'] if top_combinations else 'None'}", flush=True)

    return render_template(
        "home.html", 
        has_checked_in_today=has_checked_in_today,
        total_checkins=total_checkins,
        average_mood=average_mood,
        current_streak=current_streak,
        ranked_habits=ranked_habits,
        top_combinations=top_combinations
    )

@main.route("/goals", methods=['GET', 'POST'])
@login_required
def goals():
    """Handle user onboarding: Save selected habits and optional user goal."""
    if request.method == 'POST':
        # Task: Store selected habits and optional user goal
        selected_habits = request.form.get('habits')
        main_goal = request.form.get('goal')
        
        # Save to the current user's profile
        if selected_habits:
            current_user.selected_habits = selected_habits
        if main_goal:
            current_user.selected_goals = main_goal
            
        db.session.commit()
        print(f"DEBUG: Onboarding saved for {current_user.email} -> Goal: {main_goal}, Habits: {selected_habits}", flush=True)
        
        flash('Onboarding complete! Welcome to your dashboard.')
        return redirect(url_for('main.dashboard'))
        
    # Goal: GET displays the onboarding form
    return render_template("goals.html")

@main.route("/checkin", methods=['GET', 'POST'])
@login_required
def checkin():
    today = datetime.now(UTC).date()
    existing_checkin = CheckIn.query.filter_by(user_id=current_user.id, date=today).first()
    
    if request.method == 'GET':
        return render_template("checkin.html", existing_checkin=existing_checkin)

    mood_score = request.form.get('mood_score') 
    habits = request.form.get('habits')         
    note = request.form.get('note')             
    
    if not mood_score:
        flash('Mood score is required!')
        return redirect(url_for('main.checkin'))
        
    try:
        mood_score = int(mood_score)
    except ValueError:
        flash('Invalid mood score format!')
        return redirect(url_for('main.checkin'))
        
    if existing_checkin:
        flash('You have already submitted your check-in for today!')
        return redirect(url_for('main.dashboard'))
    
    new_checkin = CheckIn(
        user_id=current_user.id,
        mood_score=mood_score,
        habits=habits,
        note=note,
        date=today
    )
    db.session.add(new_checkin)
    db.session.commit()
    flash('Daily check-in saved successfully!')
    return redirect(url_for('main.dashboard'))

@main.route("/premium-insights")
@login_required
@premium_required
def premium_insights():
    """A premium-only feature for testing."""
    return "Welcome to Premium Insights!"