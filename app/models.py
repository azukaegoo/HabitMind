from . import db
from datetime import datetime, UTC
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    plan = db.Column(db.String(20), default="free")  # free / premium
    selected_goals = db.Column(db.String(200), nullable=True)
    onboarding_completed = db.Column(db.Boolean, default=False)

    reflection_tone = db.Column(db.String(30), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    habits = db.relationship("UserHabit", backref="user", lazy=True)
    checkins = db.relationship("CheckIn", backref="user", lazy=True)
    current_insight = db.relationship("CurrentInsight", backref="user", uselist=False)
    insight_reports = db.relationship("InsightReport", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_premium(self):
        return self.plan == "premium"

    def is_free(self):
        return self.plan == "free"


class Habit(db.Model):
    __tablename__ = "habits"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)


class UserHabit(db.Model):
    __tablename__ = "user_habits"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    habit_id = db.Column(db.Integer, db.ForeignKey("habits.id"), nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    habit = db.relationship("Habit", backref="user_habits")


class CheckIn(db.Model):
    __tablename__ = "check_ins"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    mood_score = db.Column(db.Integer, nullable=False)

    date = db.Column(
        db.Date,
        default=lambda: datetime.now(UTC).date(),
        nullable=False
    )

    note = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    habits = db.relationship("CheckInHabit", backref="checkin", lazy=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", name="_user_daily_checkin_uc"),
    )


class CheckInHabit(db.Model):
    __tablename__ = "checkin_habits"

    id = db.Column(db.Integer, primary_key=True)

    checkin_id = db.Column(db.Integer, db.ForeignKey("check_ins.id"), nullable=False)
    habit_id = db.Column(db.Integer, db.ForeignKey("habits.id"), nullable=False)

    habit = db.relationship("Habit", backref="checkin_habits")


class CurrentInsight(db.Model):
    __tablename__ = "current_insights"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)

    checkin_count = db.Column(db.Integer, default=0)
    average_mood = db.Column(db.Float, nullable=False)

    top_habits_json = db.Column(db.Text, nullable=True)
    what_we_noticed = db.Column(db.Text, nullable=True)

    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )


class InsightReport(db.Model):
    __tablename__ = "insight_reports"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)

    checkin_count = db.Column(db.Integer, default=0)
    average_mood = db.Column(db.Float, nullable=False)

    top_habits_json = db.Column(db.Text, nullable=True)
    what_we_noticed = db.Column(db.Text, nullable=True)
    goals_snapshot = db.Column(db.String(200), nullable=True)
    habits_snapshot_json = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    premium_insight = db.relationship(
        "PremiumInsight",
        backref="insight_report",
        uselist=False,
        lazy=True
    )


class PremiumInsight(db.Model):
    __tablename__ = "premium_insights"

    id = db.Column(db.Integer, primary_key=True)

    insight_report_id = db.Column(
        db.Integer,
        db.ForeignKey("insight_reports.id"),
        nullable=False
    )

    reflection_text = db.Column(db.Text, nullable=True)
    reflection_source = db.Column(db.String(30), nullable=True)

    recommendations_json = db.Column(db.Text, nullable=True)
    recommendation_source = db.Column(db.String(30), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
