from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from .config import Config
import logging.config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize logging
    logging.config.dictConfig(app.config['LOGGING'])

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = 'auth.login'

    # Register blueprints
    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.courses import courses_bp
    from .routes.cart import cart_bp
    from .routes.payment import payment_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(courses_bp, url_prefix='/courses')
    app.register_blueprint(cart_bp, url_prefix='/cart')
    app.register_blueprint(payment_bp, url_prefix='/payment')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app 