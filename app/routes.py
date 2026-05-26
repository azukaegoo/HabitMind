from flask import Blueprint, render_template, request, redirect, url_for, flash
from . import db
from .models import OneAppButton
import logging

logger = logging.getLogger(__name__)
main = Blueprint("main", __name__)


@main.route("/")
def home():
    return render_template("home.html")


@main.route("/signup")
def signup():
    return render_template("signup.html")


@main.route("/login")
def login():
    return render_template("login.html")


@main.route("/goals")
def goals():
    return render_template("goals.html")


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