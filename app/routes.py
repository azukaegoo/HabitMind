from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from . import db
import logging
from flask_login import login_required, current_user, logout_user
from datetime import datetime, UTC, timedelta
from sqlalchemy import func
from itertools import combinations
from collections import Counter
from .models import User, CheckIn, WeeklyInsight

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

# ═══════════════════════════════════════════
# HOME
# ═══════════════════════════════════════════
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
    habit_pairs = []
    for checkin in all_checkins:
        if checkin.mood_score >= 4 and checkin.habits:
            habits_list = sorted([h.strip() for h in checkin.habits.split(',') if h.strip()])
            if len(habits_list) >= 2:
                pairs = list(combinations(habits_list, 2))
                habit_pairs.extend(pairs)
                
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

# ═══════════════════════════════════════════
# ONBOARDING
# ═══════════════════════════════════════════
@main.route("/goals", methods=['GET', 'POST'])
@login_required
def goals():
    """Handle user onboarding: Save selected habits and optional user goal."""
    if request.method == 'POST':
        selected_habits = request.form.get('habits')
        main_goal = request.form.get('goal')
        
        if selected_habits:
            current_user.selected_habits = selected_habits
        if main_goal:
            current_user.selected_goals = main_goal
            
        db.session.commit()
        print(f"DEBUG: Onboarding saved for {current_user.email} -> Goal: {main_goal}, Habits: {selected_habits}", flush=True)
        
        flash('Onboarding complete! Welcome to your dashboard.')
        return redirect(url_for('main.dashboard'))
        
    return render_template("goals.html")

# ═══════════════════════════════════════════
# CHECK-IN
# ═══════════════════════════════════════════
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

# ═══════════════════════════════════════════
# PREMIUM
# ═══════════════════════════════════════════
@main.route("/premium-insights")
@login_required
@premium_required
def premium_insights():
    """A premium-only feature for testing."""
    return "Welcome to Premium Insights!"

# ═══════════════════════════════════════════
# INSIGHTS
# ═══════════════════════════════════════════
@main.route("/insights", methods=['GET'])
@login_required
def view_insights():
    """Goal: Users can view previous insight summaries."""
    past_insights = WeeklyInsight.query.filter_by(user_id=current_user.id).order_by(WeeklyInsight.end_date.desc()).all()
    return render_template("insights.html", insights=past_insights)

@main.route("/insights/history", methods=['GET'])
@login_required
def insights_history():
    """List of past insight reports for the user."""
    past_insights = WeeklyInsight.query.filter_by(user_id=current_user.id).order_by(WeeklyInsight.end_date.desc()).all()
    return render_template("insight_history.html", records=past_insights, selected_period="1m")

@main.route("/insights/generate", methods=['POST'])
@login_required
def generate_insight():
    """Task: Create weekly insight model and save summary, average mood, and top habits."""
    today = datetime.now(UTC).date()
    week_ago = today - timedelta(days=7)

    recent_checkins = CheckIn.query.filter(
        CheckIn.user_id == current_user.id,
        CheckIn.date > week_ago,
        CheckIn.date <= today
    ).all()

    if not recent_checkins:
        flash("Not enough data to generate a weekly insight.")
        return redirect(url_for('main.view_insights'))

    total_mood = sum(c.mood_score for c in recent_checkins)
    avg_mood = round(total_mood / len(recent_checkins), 1)

    habit_list = []
    for c in recent_checkins:
        if c.habits:
            habit_list.extend([h.strip() for h in c.habits.split(',') if h.strip()])

    top_habits_str = ""
    if habit_list:
        most_common = Counter(habit_list).most_common(3)
        top_habits_str = ", ".join([h[0] for h in most_common])

    new_insight = WeeklyInsight(
        user_id=current_user.id,
        start_date=week_ago + timedelta(days=1),
        end_date=today,
        average_mood=avg_mood,
        top_habits=top_habits_str,
        summary=f"Your average mood was {avg_mood}. Great job focusing on {top_habits_str}!"
    )

    db.session.add(new_insight)
    db.session.commit()
    
    flash("Weekly insight generated successfully!")
    return redirect(url_for('main.view_insights'))

# ═══════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════
@main.route("/profile", methods=['GET'])
@login_required
def profile():
    """Goal: Provide user profile information."""
    user_id = current_user.id
    today = datetime.now(UTC).date()
    
    total_checkins = CheckIn.query.filter_by(user_id=user_id).count()
    
    avg_mood_result = db.session.query(func.avg(CheckIn.mood_score)).filter_by(user_id=user_id).scalar()
    average_mood = round(avg_mood_result, 1) if avg_mood_result else 0.0
    
    checkins = CheckIn.query.filter_by(user_id=user_id).order_by(CheckIn.date.desc()).all()
    streak = 0
    if checkins:
        first_date = checkins[0].date
        if first_date == today or first_date == today - timedelta(days=1):
            streak = 1
            expected_date = first_date - timedelta(days=1)
            for i in range(1, len(checkins)):
                if checkins[i].date == expected_date:
                    streak += 1
                    expected_date -= timedelta(days=1)
                else:
                    break

    return render_template(
        "profile.html", 
        user=current_user,
        total_checkins=total_checkins,
        average_mood=average_mood,
        streak=streak  
    )

# ═══════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════
@main.route("/settings", methods=['GET'])
@login_required
def settings():
    """Goal: Allow users to view settings."""
    return render_template("settings.html")

@main.route("/settings/update", methods=['POST'])
@login_required
def update_settings():
    """Task: Update account details."""
    new_email = request.form.get('email')
    
    if new_email:
        current_user.email = new_email
    
    db.session.commit()
    flash("Settings updated successfully!")
    return redirect(url_for('main.settings'))

@main.route("/settings/cancel-premium", methods=['POST'])
@login_required
def cancel_premium():
    """Task: Unsubscribe from premium."""
    user = db.session.get(User, current_user.id)

    if user.plan == 'premium':
        user.plan = 'free'
        db.session.commit()
        flash("Your Premium subscription has been cancelled.")
    
    return redirect(url_for('main.settings'))
    
@main.route("/settings/delete-account", methods=['POST'])
@login_required
def delete_account():
    """Task: Account deletion."""
    user_id = current_user.id
    
    CheckIn.query.filter_by(user_id=user_id).delete()
    WeeklyInsight.query.filter_by(user_id=user_id).delete()
    
    user_to_delete = db.session.get(User, user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    
    logout_user()
    flash("Your account has been permanently deleted.")
    return redirect(url_for('main.home'))