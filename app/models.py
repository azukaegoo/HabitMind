from . import db
from datetime import datetime, UTC
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    plan = db.Column(db.String(20), default='free') # 'free' or 'premium'
    
    selected_goals = db.Column(db.String(200), nullable=True) 
    
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