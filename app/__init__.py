from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)

    from . import models
    from .routes import main
    app.register_blueprint(main)

    # Register the authentication blueprint
    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app