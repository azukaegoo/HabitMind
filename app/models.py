from . import db
from datetime import datetime, UTC
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    theme_preference = db.Column(db.String(50), default='light')
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    plan = db.Column(db.String(20), default='free') # 'free' or 'premium'
    
    selected_goals = db.Column(db.String(200), nullable=True)
    selected_habits = db.Column(db.String(255), nullable=True) 
    
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(UTC),
                           nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_premium(self):
        return self.plan == 'premium'

    def is_free(self):
        return self.plan == 'free'

    def __repr__(self):
        return f"<User {self.id}: {self.email}>"

class CheckIn(db.Model):
    __tablename__ = 'check_ins'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mood_score = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, default=lambda: datetime.now(UTC).date(), nullable=False)
    habits = db.Column(db.String(200), nullable=True) 
    note = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='_user_daily_checkin_uc'),
    )

    def __repr__(self):
        return f"<CheckIn User {self.user_id} on {self.date}: Mood {self.mood_score}>"

class WeeklyInsight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    average_mood = db.Column(db.Float, nullable=False)
    top_habits = db.Column(db.String(255), nullable=True)
    summary = db.Column(db.Text, nullable=True)

    user = db.relationship('User', backref=db.backref('weekly_insights', lazy=True))