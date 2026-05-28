from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config
from flask_migrate import Migrate
from flask_login import LoginManager  

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()  


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  

    from .models import User 

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from . import models
    from .routes import main
    app.register_blueprint(main)

    # Register the authentication blueprint
    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    return app