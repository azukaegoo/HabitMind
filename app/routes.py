from flask import Blueprint, render_template, request, redirect, url_for, flash
from . import db
from .models import OneAppButton
import logging

logger = logging.getLogger(__name__)
main = Blueprint("main", __name__)


# ═══════════════════════════════════════════
# HOME
# ═══════════════════════════════════════════
@main.route("/")
def home():
    return render_template("home.html")


# ═══════════════════════════════════════════
# AUTH (signup, login, forgot password)
# ═══════════════════════════════════════════
@main.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        # backend: create user account
        return redirect(url_for("main.goals"))
    return render_template("signup.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # backend: verify user credentials
        return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@main.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        # Backend will handle email sending later
        return redirect(url_for("main.check_email"))
    return render_template("forgot_password.html")


@main.route("/check-email")
def check_email():
    return render_template("check_email.html")


# ═══════════════════════════════════════════
# ONBOARDING (goals → habits → complete)
# ═══════════════════════════════════════════
@main.route("/goals", methods=["GET", "POST"])
def goals():
    if request.method == "POST":
        selected_goals = request.form.get("goals")
        # backend: save the goals to database
        return redirect(url_for("main.habits"))
    return render_template("goals.html")


@main.route("/habits", methods=["GET", "POST"])
def habits():
    if request.method == "POST":
        selected_habits = request.form.get("habits")
        # backend: save the habits to database
        return redirect(url_for("main.complete"))
    return render_template("habits.html")


@main.route("/complete")
def complete():
    return render_template("onboarding_complete.html")


# ═══════════════════════════════════════════
# DASHBOARD & CHECK-IN
# ═══════════════════════════════════════════
@main.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@main.route("/check-in", methods=["GET", "POST"])
def check_in():
    if request.method == "POST":
        mood = request.form.get("mood")
        habits_done = request.form.get("habits_done")
        # backend: save check-in to database
        return redirect(url_for("main.check_in_complete"))
    # For now, no habits passed (backend will add them)
    return render_template("check_in.html", habits=[])


@main.route("/check-in-complete")
def check_in_complete():
    return render_template("check_in_complete.html")


# ═══════════════════════════════════════════
# ONE BUTTON APP (demo)
# ═══════════════════════════════════════════
@main.route("/submit", methods=["POST"])
def submit():
    try:
        one_button = OneAppButton(value="button_clicked")
        db.session.add(one_button)
        db.session.commit()
        flash("Button click saved successfully.")
    except Exception as e:
        db.session.rollback()
        logger.exception("Database error while saving button click: %s", e)
        flash("Could not save button click.")
    return redirect(url_for("main.home"))