import logging
import os
from datetime import timedelta
from pathlib import Path

import click
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
            Path(Config.DATA_DIR).mkdir(parents=True, exist_ok=True)

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

    @app.cli.command("add-user")
    @click.argument("username")
    @click.argument("password")
    @click.option("--admin", is_flag=True, help="Set user as admin")
    def add_user_command(username, password, admin):
        """Add a new user."""
        with app.app_context():
            try:
                create_user(username, password, is_admin=admin)
                click.echo(f"User '{username}' added successfully.")
            except Exception as e:
                click.echo(f"Error adding user: {e}")

    @app.cli.command("remove-user")
    @click.argument("username")
    def remove_user_command(username):
        """Remove a user."""
        from app.services.user_service import delete_user
        
        with app.app_context():
            if delete_user(username):
                click.echo(f"User '{username}' removed successfully.")
            else:
                click.echo(f"User '{username}' not found.")

    @app.cli.command("list-users")
    def list_users_command():
        """List all users."""
        from app.models import User
        
        with app.app_context():
            users = db_session.query(User).all()
            if not users:
                click.echo("No users found.")
                return
            
            click.echo(f"{'Username':<20} {'Role':<10}")
            click.echo("-" * 30)
            for user in users:
                role = "Admin" if user.is_admin else "User"
                click.echo(f"{user.username:<20} {role:<10}")

    return app
