from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from . import db
from .models import OneAppButton
import logging

logger = logging.getLogger(__name__)
main = Blueprint("main", __name__)

# Login required decorator: Redirects unauthorized users to the login page
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@main.route("/")
def home():
    # If already logged in, go to dashboard. Otherwise, go to login.
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main.route("/dashboard")
@login_required
def dashboard():
    return render_template("home.html")

# Redirect old routes to the new auth blueprint to prevent breaking existing links
@main.route("/signup")
def signup():
    return redirect(url_for('auth.register'))

@main.route("/login")
def old_login():
    return redirect(url_for('auth.login'))

@main.route("/goals")
@login_required
def goals():
    return render_template("goals.html")

@main.route("/submit", methods=["POST"])
@login_required
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
    return redirect(url_for("main.dashboard"))