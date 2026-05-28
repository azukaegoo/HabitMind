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

@main.route("/goals")
@login_required
def goals():
    return render_template("goals.html")