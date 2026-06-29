from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
from functools import wraps
from . import db
import logging
import io
import csv
from .services.insight_helpers import (
    get_location_recommendations,
    build_top_habits,
    generate_noticed_patterns,
    generate_reflection
)
import json
from flask_login import login_required, current_user, logout_user
from datetime import datetime, UTC, timedelta
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from collections import defaultdict
from .models import User, Habit, UserHabit, CheckIn, CheckInHabit, CurrentInsight, InsightReport, PremiumInsight

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

    if not checkins:
        return 0

    latest_date = checkins[0].date

    if latest_date == today:
        expected_date = today
    elif latest_date == today - timedelta(days=1):
        expected_date = today - timedelta(days=1)
    else:
        return 0

    streak = 0

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

    saved_premium_report = InsightReport.query.filter_by(
        user_id=current_user.id
    ).first()

    can_view_insights = (
            total_checkins >= 5
            or saved_premium_report is not None
    )

    return render_template(
        "dashboard.html",
        user=current_user,
        has_checked_in_today=has_checked_in_today,
        today_checkin=today_checkin,
        total_checkins=total_checkins,
        avg_mood=avg_mood,
        mood_emoji=mood_emoji,
        streak=streak,
        can_view_insights=can_view_insights
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


# ═══════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════

@main.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


@main.route("/settings/update-tone", methods=["POST"])
@login_required
def update_tone():
    if not current_user.is_premium():
        flash("This feature is only available for premium users.", "error")
        return redirect(url_for("main.settings", open="reflection"))

    tone = request.form.get("tone")
    allowed_tones = ["supportive", "balanced", "challenge"]

    if tone not in allowed_tones:
        flash("Please select a valid tone.", "error")
        return redirect(url_for("main.settings", open="reflection"))

    try:
        current_user.reflection_tone = tone
        db.session.commit()
        flash("Reflection tone updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        logger.exception("Error updating tone for user %s: %s", current_user.email, e)
        flash("Could not update reflection tone.", "error")

    return redirect(url_for("main.settings", open="reflection"))


@main.route("/settings/upgrade-premium", methods=["POST"])
@login_required
def upgrade_premium():
    try:
        current_user.plan = "premium"
        db.session.commit()
        flash("Your account has been upgraded to Premium.", "success")
    except Exception as e:
        db.session.rollback()
        logger.exception("Error upgrading user %s: %s", current_user.email, e)
        flash("Could not upgrade your account.", "error")

    return redirect(url_for("main.settings", open="reflection"))


@main.route("/settings/cancel-premium", methods=["POST"])
@login_required
def cancel_premium():
    try:
        current_user.plan = "free"
        current_user.reflection_tone = None

        reports = InsightReport.query.filter_by(user_id=current_user.id).all()

        for report in reports:
            if report.premium_insight:
                db.session.delete(report.premium_insight)

        db.session.commit()

        flash("Premium subscription cancelled. Your account is now on the free plan.", "success")
    except Exception as e:
        db.session.rollback()
        logger.exception("Error cancelling premium for user %s: %s", current_user.email, e)
        flash("Could not cancel premium.", "error")

    return redirect(url_for("main.settings", open="danger"))


@main.route("/settings/export", methods=["POST"])
@login_required
def export_data():

    if not current_user.is_premium():
        flash("Data export is available for premium users only.", "error")
        return redirect(url_for("main.settings", open="data"))

    includes = request.form.getlist("include")

    checkins = (
        CheckIn.query
        .filter_by(user_id=current_user.id)
        .order_by(CheckIn.date.desc())
        .all()
    )

    reports = (
        InsightReport.query
        .filter_by(user_id=current_user.id)
        .order_by(InsightReport.created_at.desc())
        .all()
    )

    if not checkins and not reports:
        flash("No data to export yet.", "error")
        return redirect(url_for("main.settings", open="data"))

    output = io.StringIO()
    writer = csv.writer(output)

    # ==========================================
    # CHECK-IN HISTORY-export data
    # ==========================================
    if "checkins" in includes:

        writer.writerow(["CHECK-IN HISTORY"])

        writer.writerow([
            "Date",
            "Mood Score",
            "Habits"
        ])

        for checkin in checkins:

            habit_names = [
                item.habit.name
                for item in checkin.habits
                if item.habit
            ]

            writer.writerow([
                checkin.date,
                checkin.mood_score,
                ", ".join(habit_names)
            ])

        writer.writerow([])

    # ==========================================
    # INSIGHT REPORTS-export data
    # ==========================================
    if "insights" in includes:

        writer.writerow(["INSIGHT REPORTS"])

        writer.writerow([
            "Period Start",
            "Period End",
            "Check-In Count",
            "Average Mood",
            "Top Habits",
            "What We Noticed",
            "Goals Snapshot",
            "Habits Snapshot",
            "Premium Reflection",
            "Recommendations"
        ])

        for report in reports:

            premium_reflection = ""
            recommendations = ""

            if report.premium_insight:
                premium_reflection = (
                    report.premium_insight.reflection_text
                    or ""
                )

                recommendations = (
                    report.premium_insight.recommendations_json
                    or ""
                )

            writer.writerow([
                report.period_start,
                report.period_end,
                report.checkin_count,
                report.average_mood,
                report.top_habits_json or "",
                report.what_we_noticed or "",
                report.goals_snapshot or "",
                report.habits_snapshot_json or "",
                premium_reflection,
                recommendations
            ])

    response = Response(
        output.getvalue(),
        mimetype="text/csv"
    )

    response.headers[
        "Content-Disposition"
    ] = "attachment; filename=habitmind_data.csv"

    return response


@main.route("/settings/clear-history", methods=["POST"])
@login_required
def clear_history():
    try:
        checkins = CheckIn.query.filter_by(user_id=current_user.id).all()

        for checkin in checkins:
            CheckInHabit.query.filter_by(checkin_id=checkin.id).delete()

        CheckIn.query.filter_by(user_id=current_user.id).delete()
        CurrentInsight.query.filter_by(user_id=current_user.id).delete()

        reports = InsightReport.query.filter_by(user_id=current_user.id).all()

        for report in reports:
            if report.premium_insight:
                db.session.delete(report.premium_insight)
            db.session.delete(report)

        db.session.commit()
        flash("Your check-in history has been cleared.", "success")

    except Exception as e:
        db.session.rollback()
        logger.exception("Error clearing history for user %s: %s", current_user.email, e)
        flash("Could not clear your history.", "error")

    return redirect(url_for("main.settings", open="danger"))


@main.route("/settings/delete-account", methods=["POST"])
@login_required
def delete_account():
    try:

        user_id = current_user.id

        checkins = CheckIn.query.filter_by(user_id=user_id).all()

        for checkin in checkins:
            CheckInHabit.query.filter_by(checkin_id=checkin.id).delete()

        CheckIn.query.filter_by(user_id=user_id).delete()
        CurrentInsight.query.filter_by(user_id=user_id).delete()
        UserHabit.query.filter_by(user_id=user_id).delete()

        reports = InsightReport.query.filter_by(user_id=user_id).all()

        for report in reports:
            if report.premium_insight:
                db.session.delete(report.premium_insight)
            db.session.delete(report)

        logout_user()

        user = db.session.get(User, user_id)
        db.session.delete(user)
        db.session.commit()

        flash("Your account has been deleted.", "success")
        return redirect(url_for("auth.signup"))

    except Exception as e:
        db.session.rollback()
        logger.exception("Error deleting account: %s", e)
        flash("Could not delete your account.", "error")
        return redirect(url_for("main.settings", open="danger"))


@main.route("/insights")
@login_required
def insights():
    today = datetime.now(UTC).date()

    # Get latest 7 check-ins only for the current insight period
    latest_checkins = (
        CheckIn.query
        .filter(
            CheckIn.user_id == current_user.id,
            CheckIn.date <= today
        )
        .order_by(CheckIn.date.desc())
        .limit(7)
        .all()
    )

    checkins = list(reversed(latest_checkins))

    if checkins:
        period_start = checkins[0].date
        period_end = checkins[-1].date
    else:
        period_start = today
        period_end = today

    date_range = (
        f"{period_start.strftime('%d %b %Y')} - "
        f"{period_end.strftime('%d %b %Y')}"
    )

    # If no check-ins yet, display empty insight page
    if not checkins:
        return render_template(
            "insights.html",
            date_range=date_range,
            checkin_done=0,
            checkin_total=7,
            avg_mood=None,
            mood_emoji=get_mood_emoji(None),
            top_habits=[],
            noticed_patterns=["Your patterns will appear here after a few check-ins."],
            is_premium=current_user.is_premium(),
            reflection=None,
            recommendations=[],
            has_history=False,
            history_mode=False
        )

    saved_premium_report = (
        InsightReport.query
        .filter_by(user_id=current_user.id)
        .order_by(InsightReport.created_at.desc())
        .first()
    )

    if len(checkins) < 5 and not saved_premium_report:
        flash("Complete at least 5 check-ins to unlock your first insight.", "error")
        return redirect(url_for("main.dashboard"))

    # Check saved insight first
    if current_user.is_free():
        existing_current = CurrentInsight.query.filter_by(
            user_id=current_user.id,
            period_start=period_start,
            period_end=period_end
        ).first()

        if existing_current:
            return render_template(
                "insights.html",
                date_range=date_range,
                checkin_done=existing_current.checkin_count,
                checkin_total=7,
                avg_mood=existing_current.average_mood,
                mood_emoji=get_mood_emoji(existing_current.average_mood),
                top_habits=json.loads(existing_current.top_habits_json or "[]"),
                noticed_patterns=json.loads(existing_current.what_we_noticed or "[]"),
                is_premium=False,
                reflection=None,
                recommendations=[],
                has_history=False,
                history_mode=False
            )

    else:
        existing_report = InsightReport.query.filter_by(
            user_id=current_user.id,
            period_start=period_start,
            period_end=period_end
        ).first()

        if existing_report:
            top_habits = json.loads(existing_report.top_habits_json or "[]")
            noticed_patterns = json.loads(existing_report.what_we_noticed or "[]")

            reflection = None
            recommendations = []


            if existing_report.premium_insight:
                reflection = {
                    "text": existing_report.premium_insight.reflection_text,
                    "habit": top_habits[0]["name"] if top_habits else None,
                    "emoji": top_habits[0]["emoji"] if top_habits else "✨"
                }

                premium = existing_report.premium_insight

                if premium.recommendations_json:
                    recommendations = json.loads(
                        premium.recommendations_json
                    )
                    print("DEBUG saved recommendations:", premium.recommendations_json, flush=True)
                else:
                    latitude = session.get("location_latitude")
                    longitude = session.get("location_longitude")

                    print("DEBUG regenerating recommendations", flush=True)
                    print("DEBUG latitude:", session.get("location_latitude"), flush=True)
                    print("DEBUG longitude:", session.get("location_longitude"), flush=True)
                    print("DEBUG habit:", top_habits[0]["name"] if top_habits else None, flush=True)

                    if latitude and longitude:
                        recommendations = get_location_recommendations(
                            latitude=latitude,
                            longitude=longitude,
                            habit_name=top_habits[0]["name"] if top_habits else "Time outdoors",
                            category=top_habits[0]["category"] if top_habits else "Mental"
                        )


                    else:
                        recommendations = []

                    if recommendations and not recommendations[0].get("is_fallback"):
                        premium.recommendations_json = json.dumps(
                            recommendations,
                            ensure_ascii=False
                        )
                        premium.recommendation_source = "location_api"
                    else:
                        premium.recommendations_json = None
                        premium.recommendation_source = "fallback"

                    db.session.commit()

            has_history = (
                    db.session.query(InsightReport.id)
                    .filter_by(user_id=current_user.id)
                    .first() is not None
            )

            return render_template(
                "insights.html",
                date_range=date_range,
                checkin_done=existing_report.checkin_count,
                checkin_total=7,
                avg_mood=existing_report.average_mood,
                mood_emoji=get_mood_emoji(existing_report.average_mood),
                top_habits=top_habits,
                noticed_patterns=noticed_patterns,
                is_premium=True,
                reflection=reflection,
                recommendations=recommendations,
                history_mode=False,
                has_history=has_history,


            )

    # Generate new insight
    checkin_done = len(checkins)
    checkin_total = 7

    avg_mood = round(
        sum(checkin.mood_score for checkin in checkins) / checkin_done,
        1
    )

    top_habits = build_top_habits(checkins)

    noticed_patterns = generate_noticed_patterns(
        checkins=checkins,
        top_habits=top_habits,
        avg_mood=avg_mood
    )

    is_premium = current_user.is_premium()

    reflection = None
    recommendations = []

    if is_premium and top_habits:
        main_habit = top_habits[0]

        reflection = generate_reflection(
            top_habits=top_habits,
            avg_mood=avg_mood,
            tone=current_user.reflection_tone
        )

        latitude = session.get("location_latitude")
        longitude = session.get("location_longitude")

        if latitude and longitude:
            recommendations = get_location_recommendations(
                latitude=latitude,
                longitude=longitude,
                habit_name=main_habit["name"],
                category=main_habit["category"]
            )
        else:
            recommendations = []

    # Save generated insight
    try:
        if current_user.is_free():
            CurrentInsight.query.filter_by(user_id=current_user.id).delete()

            current_insight = CurrentInsight(
                user_id=current_user.id,
                period_start=period_start,
                period_end=period_end,
                checkin_count=checkin_done,
                average_mood=avg_mood,
                top_habits_json=json.dumps(top_habits, ensure_ascii=False),
                what_we_noticed=json.dumps(noticed_patterns, ensure_ascii=False)
            )

            db.session.add(current_insight)

        else:
            insight_report = InsightReport.query.filter_by(
                user_id=current_user.id,
                period_start=period_start,
                period_end=period_end
            ).first()

            if not insight_report:
                insight_report = InsightReport(
                    user_id=current_user.id,
                    period_start=period_start,
                    period_end=period_end,
                    checkin_count=checkin_done,
                    average_mood=avg_mood,
                    top_habits_json=json.dumps(top_habits, ensure_ascii=False),
                    what_we_noticed=json.dumps(noticed_patterns, ensure_ascii=False),
                    goals_snapshot=current_user.selected_goals,
                    habits_snapshot_json=json.dumps(top_habits, ensure_ascii=False)
                )

                db.session.add(insight_report)
                db.session.flush()
            else:
                insight_report.checkin_count = checkin_done
                insight_report.average_mood = avg_mood
                insight_report.top_habits_json = json.dumps(top_habits, ensure_ascii=False)
                insight_report.what_we_noticed = json.dumps(noticed_patterns, ensure_ascii=False)
                insight_report.goals_snapshot = current_user.selected_goals
                insight_report.habits_snapshot_json = json.dumps(top_habits, ensure_ascii=False)

            if reflection:

                recommendations_json = None
                recommendation_source = None

                if recommendations:
                    if recommendations[0].get("is_fallback"):
                        recommendation_source = "fallback"
                    else:
                        recommendations_json = json.dumps(
                            recommendations,
                            ensure_ascii=False
                        )
                        recommendation_source = "location_api"

                premium_insight = PremiumInsight(
                    insight_report_id=insight_report.id,
                    reflection_text=reflection["text"],
                    reflection_source="json_template",

                    recommendations_json=recommendations_json,
                    recommendation_source=recommendation_source,

                    location_latitude=session.get("location_latitude"),
                    location_longitude=session.get("location_longitude"),
                    location_label="Browser location" if session.get("location_latitude") else None
                )

                db.session.add(premium_insight)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logger.exception(
            "Error saving insight for user %s: %s",
            current_user.email,
            e
        )

    has_history = (
            db.session.query(InsightReport.id)
            .filter_by(user_id=current_user.id)
            .first() is not None
    )
    return render_template(
        "insights.html",
        date_range=date_range,
        checkin_done=checkin_done,
        checkin_total=checkin_total,
        avg_mood=avg_mood,
        mood_emoji=get_mood_emoji(avg_mood),
        top_habits=top_habits,
        noticed_patterns=noticed_patterns,
        is_premium=is_premium,
        reflection=reflection,
        recommendations=recommendations,
        has_history=has_history,
        history_mode=False
    )


@main.route("/save-location", methods=["POST"])
@login_required
def save_location():
    data = request.get_json()

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if latitude is None or longitude is None:
        return {"success": False}, 400

    session["location_latitude"] = float(latitude)
    session["location_longitude"] = float(longitude)
    logger.info(
        "Location saved: %s %s",
        latitude,
        longitude
    )
    return {"success": True}


@main.route("/insights/history")
@login_required
@premium_required
def insight_history():
    reports = (
        InsightReport.query
        .filter_by(user_id=current_user.id)
        .order_by(InsightReport.created_at.desc())
        .all()
    )

    if not reports:
        flash(
            "Your completed insight reports will appear here after your first insight cycle.",
            "info"
        )
        return redirect(url_for("main.insights"))

    selected_period = request.args.get("period", "1m")

    today = datetime.now(UTC).date()

    period_days = {
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "1y": 365
    }

    days = period_days.get(selected_period, 30)
    start_date = today - timedelta(days=days)

    reports = (
        InsightReport.query
        .filter(
            InsightReport.user_id == current_user.id,
            InsightReport.period_start >= start_date
        )
        .order_by(InsightReport.created_at.desc())
        .all()
    )

    records = []

    for report in reports:
        records.append({
            "id": report.id,
            "date_range": (
                f"{report.period_start.strftime('%d %b %Y')} - "
                f"{report.period_end.strftime('%d %b %Y')}"
            ),
            "days": report.checkin_count,
            "average_mood": report.average_mood,
            "checkin_count": report.checkin_count
        })

    return render_template(
        "insight_history.html",
        selected_period=selected_period,
        records=records,
        get_mood_emoji=get_mood_emoji
    )

@main.route("/insights/history/<int:report_id>")
@login_required
@premium_required
def insight_detail(report_id):
    report = (
        InsightReport.query
        .filter_by(
            id=report_id,
            user_id=current_user.id
        )
        .first_or_404()
    )

    premium = report.premium_insight

    top_habits = json.loads(report.top_habits_json or "[]")
    noticed_patterns = json.loads(report.what_we_noticed or "[]")

    reflection = None
    recommendations = []

    if premium:
        if premium.reflection_text:
            reflection = {
                "text": premium.reflection_text,
                "habit": top_habits[0]["name"] if top_habits else None,
                "emoji": top_habits[0]["emoji"] if top_habits else "✨"
            }

        if premium.recommendations_json:
            recommendations = json.loads(premium.recommendations_json)

    date_range = (
        f"{report.period_start.strftime('%d %b %Y')} - "
        f"{report.period_end.strftime('%d %b %Y')}"
    )

    return render_template(
        "insights.html",
        date_range=date_range,
        checkin_done=report.checkin_count,
        checkin_total=7,
        avg_mood=report.average_mood,
        mood_emoji=get_mood_emoji(report.average_mood),
        top_habits=top_habits,
        noticed_patterns=noticed_patterns,
        is_premium=True,
        reflection=reflection,
        recommendations=recommendations,
        history_mode=True
    )



'''
# ═══════════════════════════════════════════════════════════════
# Development Utilities (Remove before production)
# ═══════════════════════════════════════════════════════════════
#
# These routes are used ONLY during development to regenerate
# different parts of the Insight feature without completing a
# new 5–7 day check-in cycle.
#
# /dev/reset-reflection
#     Clears the saved reflection only.
#     The next visit to /insights regenerates the reflection
#     using the latest reflection engine and tone templates.
#
# /dev/reset-recommendations
#     Clears the saved location recommendations only.
#     The next visit to /insights calls the recommendation APIs
#     (OpenStreetMap/Ticketmaster or future providers) again.
#
# /dev/reset-latest-insight
#     Deletes the latest saved insight snapshot
#     (InsightReport + PremiumInsight) without deleting
#     any user check-ins.
#
#     This forces the entire insight to regenerate using the
#     existing check-in data and is useful when testing changes
#     to:
#         • Top Habits
#         • What We Noticed
#         • Reflection generation
#         • Recommendation generation
#         • Insight snapshot saving
#
# NOTE:
# These routes should NOT be available in production.
# Remove them or restrict them to Flask DEBUG mode before deployment.
# ═══════════════════════════════════════════════════════════════


@main.route("/dev/reset-recommendations")
@login_required
def reset_recommendations():

    latest_report = (
        InsightReport.query
        .filter_by(user_id=current_user.id)
        .order_by(InsightReport.created_at.desc())
        .first()
    )

    if not latest_report or not latest_report.premium_insight:
        flash("No premium insight found.", "warning")
        return redirect(url_for("main.insights"))

    premium = latest_report.premium_insight

    premium.recommendations_json = None
    premium.recommendation_source = None

    db.session.commit()

    flash(
        "Recommendations reset. Refresh Insights to generate new recommendations.",
        "success"
    )

    return redirect(url_for("main.insights"))

@main.route("/dev/reset-latest-insight")
@login_required
def reset_latest_insight():
    if current_user.is_free():
        current = CurrentInsight.query.filter_by(
            user_id=current_user.id
        ).first()

        if current:
            db.session.delete(current)
            db.session.commit()
            flash("Current insight reset. It will regenerate from existing check-ins.", "success")
        else:
            flash("No current insight found.", "warning")

        return redirect(url_for("main.insights"))

    latest_report = (
        InsightReport.query
        .filter_by(user_id=current_user.id)
        .order_by(InsightReport.created_at.desc())
        .first()
    )

    if latest_report:
        if latest_report.premium_insight:
            db.session.delete(latest_report.premium_insight)

        db.session.delete(latest_report)
        db.session.commit()

        flash("Latest premium insight reset. It will regenerate from existing check-ins.", "success")
    else:
        flash("No premium insight report found.", "warning")

    return redirect(url_for("main.insights"))

@main.route("/dev/reset-reflection")
@login_required
def reset_reflection():
    latest_report = (
        InsightReport.query
        .filter_by(user_id=current_user.id)
        .order_by(InsightReport.created_at.desc())
        .first()
    )

    if not latest_report or not latest_report.premium_insight:
        flash("No premium insight found.", "warning")
        return redirect(url_for("main.insights"))

    premium = latest_report.premium_insight
    premium.reflection_text = None
    premium.reflection_source = None

    db.session.commit()

    flash("Reflection reset. Refresh Insights to generate a new reflection.", "success")
    return redirect(url_for("main.insights"))

@main.route("/dev/clear-insight-history")
@login_required
def clear_insight_history():

    reports = InsightReport.query.filter_by(
        user_id=current_user.id
    ).all()

    for report in reports:
        if report.premium_insight:
            db.session.delete(report.premium_insight)

        db.session.delete(report)

    current = CurrentInsight.query.filter_by(
        user_id=current_user.id
    ).first()

    if current:
        db.session.delete(current)

    db.session.commit()

    flash("Insight history cleared.", "success")
    return redirect(url_for("main.dashboard"))

'''