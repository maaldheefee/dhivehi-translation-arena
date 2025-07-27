import logging
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g

from app import database
from app.blueprints.auth import auth_bp
from app.blueprints.main import main_bp
from app.blueprints.stats import stats_bp
from app.config import Config
from app.database import db_session, init_db, shutdown_session
from app.i18n import TRANSLATIONS
from app.models import Base, User
from app.services.user_service import create_user


def create_app():
    # Load environment variables from .env file
    if os.getenv("FLASK_ENV") != "production":
        load_dotenv()

    # Initialize logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # Load configuration from config.py
    app.config.from_object(Config)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24).hex())
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    # Initialize database
    init_db(app)

    @app.before_request
    def before_request():
        # Set language from session or default to English
        # g.lang = session.get('lang', 'en')
        # Hardcode language to Dhivehi
        g.lang = "dv"

    app.teardown_appcontext(shutdown_session)

    @app.context_processor
    def inject_vars():
        def _(key, **kwargs):
            return TRANSLATIONS.get(g.lang, {}).get(key, key).format(**kwargs)

        return {"_": _}

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(stats_bp, url_prefix="/stats")

    @app.cli.command("init-db")
    def init_db_command():
        """Initialize the database with default users."""
        with app.app_context():
            Path("data").mkdir(parents=True, exist_ok=True)

            print("Initializing database...")
            Base.metadata.create_all(bind=database.engine, checkfirst=True)
            print("Database schema checked/created successfully.")

            default_users = [
                {"username": "Hassaan", "password": "1234", "is_admin": True},
                {"username": "John", "password": "1234", "is_admin": False},
            ]

            user_count = db_session.query(User).count()
            if user_count == 0:
                print("No users found, creating default users...")
                for user_data in default_users:
                    create_user(
                        username=user_data["username"],
                        password=user_data["password"],
                        is_admin=user_data["is_admin"],
                    )
                print("Default users created successfully!")
            else:
                print(
                    f"{user_count} users already exist, skipping default user creation."
                )

    return app
