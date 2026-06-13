from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from . import db
import logging
from flask_login import login_required, current_user, logout_user
from datetime import datetime, UTC, timedelta
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from itertools import combinations
from collections import Counter, defaultdict
from .models import User, Habit, UserHabit, CheckIn, CheckInHabit, CurrentInsight

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
# Helper functions
# ═══════════════════════════════════════════
def calculate_streak(user_id):
    today = datetime.now(UTC).date()

    checkins = (
        CheckIn.query
        .filter_by(user_id=user_id)
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

    return streak


def get_mood_emoji(avg_mood):
    if avg_mood is None:
        return "—"

    rounded_mood = round(avg_mood)

    mood_emojis = {
        1: "😭",
        2: "😰",
        3: "😟",
        4: "🙁",
        5: "😐",
        6: "🙂",
        7: "😊",
        8: "😄",
        9: "😁",
        10: "🤩",
    }

    return mood_emojis.get(rounded_mood, "😐")


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
# ONBOARDING - GOALS
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

            flash(
                "Could not save your goal selections. Please try again.",
                "error"
            )

            return redirect(url_for("main.goals"))

    return render_template("goals.html",
                           is_edit=False,
                           selected_goals=[])


# ═══════════════════════════════════════════
# ONBOARDING - SELECT HABIT
# ═══════════════════════════════════════════
@main.route("/habits", methods=["GET", "POST"])
@login_required
def habits():
    """Handle onboarding Step 2: Save selected habits."""

    if current_user.onboarding_completed:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        try:
            selected_habits = request.form.get("habits", "")

            habit_ids = [
                int(habit_id)
                for habit_id in selected_habits.split(",")
                if habit_id.strip()
            ]

            if len(habit_ids) < 5 or len(habit_ids) > 7:
                return redirect(url_for("main.habits"))

            for habit_id in habit_ids:
                user_habit = UserHabit(
                    user_id=current_user.id,
                    habit_id=habit_id
                )
                db.session.add(user_habit)

            current_user.onboarding_completed = True

            db.session.commit()

            return redirect(url_for("main.dashboard"))

        except Exception as e:
            db.session.rollback()

            logger.exception(
                "Error saving habits for user %s: %s",
                current_user.email,
                e
            )

            flash(
                "Could not save your habit selections. Please try again.",
                "error"
            )

            return redirect(url_for("main.habits"))

    all_habits = Habit.query.filter_by(
        is_active=True
    ).all()

    habits_by_category = defaultdict(list)

    for habit in all_habits:
        habits_by_category[habit.category].append(habit)

    return render_template(
        "habits.html",
        habits_by_category=habits_by_category,
        is_edit=False,
        selected_habit_ids=[]
    )


# ═══════════════════════════════════════════
# DASHBOARD
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

    # Total check-ins
    total_checkins = CheckIn.query.filter_by(
        user_id=current_user.id
    ).count()

    # Average mood (associated with all checkins)
    avg_mood = (
        db.session.query(func.avg(CheckIn.mood_score))
        .filter(CheckIn.user_id == current_user.id)
        .scalar()
    )

    if avg_mood is not None:
        avg_mood = round(avg_mood, 1)

    mood_emoji = get_mood_emoji(avg_mood)

    # streak calculations
    streak = calculate_streak(current_user.id)

    return render_template(
        "dashboard.html",
        user=current_user,
        has_checked_in_today=has_checked_in_today,
        today_checkin=today_checkin,
        total_checkins=total_checkins,
        avg_mood=avg_mood,
        mood_emoji=mood_emoji,
        streak=streak
    )


# ═══════════════════════════════════════════
# DAILY CHECK-IN
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
        flash("You have already completed today's check-in.")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        try:
            mood_value = request.form.get("mood")
            habits_done = request.form.get("habits_done", "")

            if not mood_value:
                flash("Please select your mood before saving.")
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

            session["checkin_completed"] = True
            return redirect(url_for("main.check_in_complete"))

        except IntegrityError:
            db.session.rollback()
            flash("You have already completed today's check-in.")
            return redirect(url_for("main.dashboard"))

        except Exception as e:
            db.session.rollback()
            logger.exception(
                "Error saving check-in for user %s: %s",
                current_user.email,
                e
            )
            flash("Could not save your check-in. Please try again.")
            return redirect(url_for("main.check_in"))

    habit_s = (
        db.session.query(Habit)
        .join(UserHabit, UserHabit.habit_id == Habit.id)
        .filter(UserHabit.user_id == current_user.id)
        .all()
    )

    return render_template("check_in.html", habits=habit_s)


@main.route("/check-in-complete")
@login_required
def check_in_complete():
    if not session.pop("checkin_completed", None):
        return redirect(url_for("main.dashboard"))

    return render_template("check_in_complete.html")


# ═══════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════
@main.route("/profile")
@login_required
def profile():
    total_checkins = CheckIn.query.filter_by(user_id=current_user.id).count()

    average_mood = (
        db.session.query(func.avg(CheckIn.mood_score))
        .filter(CheckIn.user_id == current_user.id)
        .scalar()
    )

    if average_mood is not None:
        average_mood = round(average_mood, 1)
    mood_emoji = get_mood_emoji(average_mood)

    selected_habits = (
        db.session.query(Habit)
        .join(UserHabit, UserHabit.habit_id == Habit.id)
        .filter(UserHabit.user_id == current_user.id)
        .all()
    )

    name_parts = current_user.name.split() if current_user.name else []
    user_initials = "".join([part[0].upper() for part in name_parts[:2]])

    if not user_initials:
        user_initials = current_user.email[0].upper()


    streak = calculate_streak(current_user.id)

    selected_goals = (
        current_user.selected_goals.split(",")
        if current_user.selected_goals
        else []
    )

    return render_template(
        "profile.html",
        user=current_user,
        user_initials=user_initials,
        total_checkins=total_checkins,
        average_mood=average_mood,
        selected_habits=selected_habits,
        selected_goals=selected_goals,
        mood_emoji=mood_emoji,
        streak=streak
    )


@main.route("/edit-goals", methods=["GET", "POST"])
@login_required
def edit_goals():
    if request.method == "POST":
        try:
            selected_goals = request.form.get("goals", "")

            goals_list = [
                goal.strip()
                for goal in selected_goals.split(",")
                if goal.strip()
            ]

            if not goals_list or len(goals_list) > 3:
                return redirect(url_for("main.edit_goals"))

            current_user.selected_goals = ",".join(goals_list)

            # Free users only have current insight, so reset it
            if current_user.is_free():
                CurrentInsight.query.filter_by(user_id=current_user.id).delete()

            db.session.commit()

            flash("Your goals were updated successfully.", "success")
            return redirect(url_for("main.profile"))

        except Exception as e:
            db.session.rollback()
            logger.exception("Error updating goals for user %s: %s", current_user.email, e)
            flash("Could not update your goals. Please try again.", "error")
            return redirect(url_for("main.edit_goals"))

    selected_goals = (
        current_user.selected_goals.split(",")
        if current_user.selected_goals
        else []
    )

    return render_template("goals.html", selected_goals=selected_goals, is_edit=True)


@main.route("/edit-habits", methods=["GET", "POST"])
@login_required
def edit_habits():
    if request.method == "POST":
        try:
            selected_habits = request.form.get("habits", "")

            habit_ids = [
                int(habit_id)
                for habit_id in selected_habits.split(",")
                if habit_id.strip()
            ]

            if len(habit_ids) < 5 or len(habit_ids) > 7:
                return redirect(url_for("main.edit_habits"))

            UserHabit.query.filter_by(user_id=current_user.id).delete()

            for habit_id in habit_ids:
                db.session.add(UserHabit(user_id=current_user.id, habit_id=habit_id))

            if current_user.is_free():
                CurrentInsight.query.filter_by(user_id=current_user.id).delete()

            db.session.commit()

            flash("Your habits were updated successfully.", "success")
            return redirect(url_for("main.profile"))

        except Exception as e:
            db.session.rollback()
            logger.exception("Error updating habits for user %s: %s", current_user.email, e)
            flash("Could not update your habits. Please try again.", "error")
            return redirect(url_for("main.edit_habits"))

    all_habits = Habit.query.filter_by(is_active=True).all()

    selected_habit_ids = [
        user_habit.habit_id
        for user_habit in UserHabit.query.filter_by(user_id=current_user.id).all()
    ]

    return render_template(
        "habits.html",
        habits=all_habits,
        selected_habit_ids=selected_habit_ids,
        is_edit=True
    )





'''
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

    print(
        f"DEBUG: Dashboard stats for {current_user.email} -> Streak: {current_streak}, Top Combo: {top_combinations[0]['pair'] if top_combinations else 'None'}",
        flush=True)

    return render_template(
        "dashboard.html",
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
    """Handle user onboarding Step 1: Save selected goals."""
    if request.method == 'POST':
        selected_goals = request.form.get('goals')

        if selected_goals:
            current_user.selected_goals = selected_goals
            db.session.commit()
            print(f"DEBUG: Goals saved for {current_user.email} -> {selected_goals}", flush=True)
        
        return redirect(url_for('main.habits')) 
        
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
    """Goal: Users can view previous insight summaries.
       Rule: Locked for new users until they reach 7 check-ins."""
       
    total_checkins = CheckIn.query.filter_by(user_id=current_user.id).count()
    
    if total_checkins < 7:
        remaining = 7 - total_checkins
        flash(f"Keep going! You need {remaining} more check-in{'s' if remaining > 1 else ''} to unlock your Insights.", "info")
        return redirect(url_for('main.dashboard'))

    past_insights = WeeklyInsight.query.filter_by(user_id=current_user.id).order_by(WeeklyInsight.end_date.desc()).all()
    return render_template("insights.html", insights=past_insights)


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
    """Task: Unsubscribe from premium and delete premium data."""
    user = db.session.get(User, current_user.id)

    if user.plan == 'premium':
        user.plan = 'free'
        
        WeeklyInsight.query.filter_by(user_id=user.id).delete()
        
        db.session.commit()
        flash("Your Premium subscription has been cancelled and premium data has been removed.")
    else:
        flash("You are not currently on a Premium plan.")
        
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

# ----------------------------------------------------
# Onboarding Step 2: Habit Selection
# ----------------------------------------------------
@main.route("/habits", methods=['GET', 'POST'])
@login_required
def habits():
    """Handle user onboarding Step 2: Save selected habits."""
    if request.method == 'POST':
        # Use the variable name 'habits' according to Notion specifications
        selected_habits = request.form.get('habits')
        
        if selected_habits:
            current_user.selected_habits = selected_habits
            db.session.commit()
            print(f"DEBUG: Habits saved for {current_user.email} -> {selected_habits}", flush=True)
            
        # Redirect to the final completion page once saved
        return redirect(url_for('main.complete'))
        
    # Render the habit selection template for GET requests
    return render_template("habits.html")

# ----------------------------------------------------
# Onboarding Step 3: Completion Screen
# ----------------------------------------------------
@main.route("/complete", methods=['GET'])
@login_required
def complete():
    """Handle user onboarding Step 3: Show completion screen."""
    # Render the onboarding complete template (the dashboard link button is in the HTML)
    return render_template("onboarding_complete.html")

import csv
from io import StringIO
from flask import make_response

@main.route("/export-data", methods=['GET'])
@login_required
def export_data():
    """Task: Export user data to CSV, with check if data exists."""
    user_id = current_user.id
    
    checkins = CheckIn.query.filter_by(user_id=user_id).order_by(CheckIn.date.desc()).all()
    
    if not checkins:
        flash("There is no data to export yet.", "error")
        return redirect(url_for('main.settings'))

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date', 'Mood Score', 'Habits', 'Notes'])
    
    for c in checkins:
        cw.writerow([c.date, c.mood_score, c.habits, c.note])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=habitmind_data.csv"
    output.headers["Content-type"] = "text/csv"
    
    return output

@main.route("/upgrade", methods=['POST'])
@login_required
def upgrade_premium():
    """Task: Upgrade user to premium plan."""
    user = db.session.get(User, current_user.id)
    
    if user.plan != 'premium':
        user.plan = 'premium'
        db.session.commit()
        flash('Successfully upgraded to Premium!', 'success')
    else:
        flash('You are already a Premium member.', 'info')
        
    return redirect(url_for('main.settings'))

'''