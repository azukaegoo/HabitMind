from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail 

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail() 

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'habitmind.team@gmail.com'
    app.config['MAIL_PASSWORD'] = 'Team_SGD' 

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app) \

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login' 

    from .models import User 

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .routes import main
    app.register_blueprint(main)

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    return app