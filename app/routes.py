from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response
from functools import wraps
import logging
import csv
from io import StringIO
from collections import Counter
from itertools import combinations
from flask_login import login_required, current_user, logout_user

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, UTC, timedelta
from flask import session
from sqlalchemy.exc import IntegrityError

from . import db
import logging
logger = logging.getLogger(__name__)

from .models import (
    User,
    Habit,
    UserHabit,
    CheckIn,
    CheckInHabit,
    CurrentInsight
)

logger = logging.getLogger(__name__)
main = Blueprint("main", __name__)

def premium_required(f):
    """Decorator to require premium plan for specific routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_premium():
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
    """Redirect to dashboard if logged in, otherwise show homepage."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template("home.html")

# ═══════════════════════════════════════════
# DASHBOARD (Azuka's Update)
# ═══════════════════════════════════════════
@main.route("/dashboard")
@login_required
def dashboard():
    today = datetime.now(UTC).date()

    today_checkin = CheckIn.query.filter_by(
        user_id=current_user.id,
        date=today
    ).first()

    has_checked_in_today = today_checkin is not None

    total_checkins = CheckIn.query.filter_by(
        user_id=current_user.id
    ).count()

    avg_mood = (
        db.session.query(func.avg(CheckIn.mood_score))
        .filter(CheckIn.user_id == current_user.id)
        .scalar()
    )

    if avg_mood is not None:
        avg_mood = round(avg_mood, 1)

    checkins = (
        CheckIn.query
        .filter_by(user_id=current_user.id)
        .order_by(CheckIn.date.desc())
        .all()
    )

    streak = 0
    expected_date = today

    for checkin in checkins:
        if checkin.date == expected_date:
            streak += 1
            expected_date -= timedelta(days=1)
        else:
            break

    return render_template(
        "dashboard.html",
        user=current_user,
        has_checked_in_today=has_checked_in_today,
        today_checkin=today_checkin,
        total_checkins=total_checkins,
        avg_mood=avg_mood,
        streak=streak
    )

# ═══════════════════════════════════════════
# ONBOARDING - GOALS & HABITS (Azuka's Update)
# ═══════════════════════════════════════════
@main.route("/goals", methods=["GET", "POST"])
@login_required
def goals():
    """Handle onboarding Step 1: Save selected goals."""
    if current_user.onboarding_completed:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        selected_goals = request.form.get("goals", "")

        goals_list = [
            goal.strip()
            for goal in selected_goals.split(",")
            if goal.strip()
        ]

        # Basic backend safety check
        if not goals_list:
            return redirect(url_for("main.goals"))

        current_user.selected_goals = ",".join(goals_list)

        try:
            db.session.commit()
            print(
                f"DEBUG: Goals saved for {current_user.email} -> {current_user.selected_goals}",
                flush=True
            )
            return redirect(url_for("main.habits"))

        except Exception as e:
            db.session.rollback()
            logger.exception(
                "Error saving goals for user %s: %s",
                current_user.email,
                e
            )
            return redirect(url_for("main.goals"))

    return render_template("goals.html")

@main.route("/habits", methods=["GET", "POST"])
@login_required
def habits():
    if current_user.onboarding_completed:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        selected_habits = request.form.get("habits", "")
        print(f"DEBUG: Form data received: '{selected_habits}'", flush=True)
        
        if not selected_habits:
            print("DEBUG: selected_habits is empty!", flush=True)
            flash("Please select at least 5 habits.", "error")
            return redirect(url_for("main.habits"))

        try:
            habit_ids = [
                int(h_id) for h_id in selected_habits.split(",") if h_id.strip().isdigit()
            ]
        except ValueError:
            flash("Invalid habit selection.", "error")
            return redirect(url_for("main.habits"))

        if len(habit_ids) < 5 or len(habit_ids) > 7:
            flash(f"Please select between 5 and 7 habits. You selected {len(habit_ids)}.", "error")
            return redirect(url_for("main.habits"))

        for habit_id in habit_ids:
            user_habit = UserHabit(
                user_id=current_user.id,
                habit_id=habit_id
            )
            db.session.add(user_habit)

        current_user.onboarding_completed = True
        db.session.commit()
        flash("Habits saved successfully!", "success")
        return redirect(url_for("main.dashboard"))

    all_habits = Habit.query.filter_by(is_active=True).all()
    return render_template("habits.html", habits=all_habits)

# ═══════════════════════════════════════════
# CHECK-IN (Azuka's Update)
# ═══════════════════════════════════════════
@main.route("/check-in", methods=["GET", "POST"])
@login_required
def check_in():
    today = datetime.now(UTC).date()

    today_checkin = CheckIn.query.filter_by(
        user_id=current_user.id,
        date=today
    ).first()

    if today_checkin:
        flash("You have already completed today's check-in.", "info")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        try:
            mood_value = request.form.get("mood")
            habits_done = request.form.get("habits_done", "")

            if not mood_value:
                flash("Please select your mood before saving.", "error")
                return redirect(url_for("main.check_in"))

            checkin = CheckIn(
                user_id=current_user.id,
                mood_score=int(mood_value),
                date=today
            )

            db.session.add(checkin)
            db.session.flush()

            habit_ids = [
                int(habit_id)
                for habit_id in habits_done.split(",")
                if habit_id.strip()
            ]

            for habit_id in habit_ids:
                db.session.add(
                    CheckInHabit(
                        checkin_id=checkin.id,
                        habit_id=habit_id
                    )
                )

            db.session.commit()
            return redirect(url_for("main.dashboard"))

        except IntegrityError:
            db.session.rollback()
            flash("You have already completed today's check-in.", "info")
            return redirect(url_for("main.dashboard"))

        except Exception as e:
            db.session.rollback()
            logger.exception("Error saving check-in for user %s: %s", current_user.email, e)
            flash("Could not save your check-in. Please try again.", "error")
            return redirect(url_for("main.check_in"))

    habits = (
        db.session.query(Habit)
        .join(UserHabit, UserHabit.habit_id == Habit.id)
        .filter(UserHabit.user_id == current_user.id)
        .all()
    )

    return render_template("check_in.html", habits=habits)


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
    total_checkins = CheckIn.query.filter_by(user_id=current_user.id).count()

    if total_checkins < 7:
        remaining = 7 - total_checkins
        flash(f"Keep going! You need {remaining} more check-in{'s' if remaining > 1 else ''} to unlock your Insights.", "info")
        return redirect(url_for('main.dashboard'))

    past_insights = InsightReport.query.filter_by(user_id=current_user.id).order_by(InsightReport.period_end.desc()).all()
    return render_template("insights.html", insights=past_insights)

@main.route("/insights/generate", methods=['POST'])
@login_required
def generate_insight():
    """Task: Create weekly insight model and save summary."""
    today = datetime.now(UTC).date()
    week_ago = today - timedelta(days=7)

    recent_checkins = CheckIn.query.filter(
        CheckIn.user_id == current_user.id,
        CheckIn.date > week_ago,
        CheckIn.date <= today
    ).all()

    if not recent_checkins:
        flash("Not enough data to generate a weekly insight.", "error")
        return redirect(url_for('main.view_insights'))

    total_mood = sum(c.mood_score for c in recent_checkins)
    avg_mood = round(total_mood / len(recent_checkins), 1)

    new_insight = InsightReport(
        user_id=current_user.id,
        period_start=week_ago + timedelta(days=1),
        period_end=today,
        checkin_count=len(recent_checkins),
        average_mood=avg_mood,
        what_we_noticed=f"Your average mood was {avg_mood} over {len(recent_checkins)} check-ins."
    )

    db.session.add(new_insight)
    db.session.commit()

    flash("Weekly insight generated successfully!", "success")
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
    expected_date = today

    for checkin in checkins:
        if checkin.date == expected_date:
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
    return render_template("settings.html")

@main.route("/settings/update", methods=['POST'])
@login_required
def update_settings():
    new_email = request.form.get('email')
    if new_email:
        current_user.email = new_email
    db.session.commit()
    flash("Settings updated successfully!", "success")
    return redirect(url_for('main.settings'))

@main.route("/settings/cancel-premium", methods=['POST'])
@login_required
def cancel_premium():
    user = db.session.get(User, current_user.id)
    if user.is_premium():
        user.plan = 'free'
        CurrentInsight.query.filter_by(user_id=user.id).delete()
        InsightReport.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        flash("Your Premium subscription has been cancelled and premium data has been removed.", "success")
    else:
        flash("You are not currently on a Premium plan.", "info")
    return redirect(url_for('main.settings'))

@main.route("/settings/delete-account", methods=['POST'])
@login_required
def delete_account():
    user_id = current_user.id
    CheckInHabit.query.join(CheckIn).filter(CheckIn.user_id == user_id).delete()
    CheckIn.query.filter_by(user_id=user_id).delete()
    UserHabit.query.filter_by(user_id=user_id).delete()
    CurrentInsight.query.filter_by(user_id=user_id).delete()
    InsightReport.query.filter_by(user_id=user_id).delete()
    
    user_to_delete = db.session.get(User, user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    logout_user()
    flash("Your account has been permanently deleted.", "success")
    return redirect(url_for('main.home'))

@main.route("/settings/upgrade-premium", methods=['POST'])
@login_required
def upgrade_premium_settings():
    user = db.session.get(User, current_user.id)
    if not user.is_premium():
        user.plan = 'premium'
        db.session.commit()
        flash('Successfully upgraded to Premium!', 'success')
    else:
        flash('You are already a Premium member.', 'info')
    return redirect(url_for('main.settings'))

@main.route("/settings/update-tone", methods=['POST'])
@login_required
def update_tone():
    new_tone = request.form.get('tone')
    if new_tone:
        current_user.reflection_tone = new_tone 
        db.session.commit()
        flash(f"Tone preference updated to {new_tone}!", 'success')
    else:
        flash("Please select a tone preference.", 'error')
    return redirect(url_for('main.settings'))

# ═══════════════════════════════════════════
# MISC
# ═══════════════════════════════════════════
@main.route("/complete", methods=['GET'])
@login_required
def complete():
    """Handle user onboarding Step 3: Show completion screen."""
    return render_template("onboarding_complete.html")

@main.route("/export-data", methods=['GET'])
@login_required
def export_data():
    user_id = current_user.id
    checkins = CheckIn.query.filter_by(user_id=user_id).order_by(CheckIn.date.desc()).all()

    if not checkins:
        flash("There is no data to export yet.", "error")
        return redirect(url_for('main.settings'))

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date', 'Mood Score', 'Habits', 'Notes'])

    for c in checkins:
        habit_names = ", ".join([ch.habit.name for ch in c.habits])
        cw.writerow([c.date, c.mood_score, habit_names, c.note])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=habitmind_data.csv"
    output.headers["Content-type"] = "text/csv"
    return output