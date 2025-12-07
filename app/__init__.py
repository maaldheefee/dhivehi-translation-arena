import logging
import os
from datetime import timedelta

from dotenv import load_dotenv  # ty:ignore[unresolved-import]
from flask import Flask, g
from flask_wtf.csrf import CSRFProtect

from app.blueprints.auth import auth_bp
from app.blueprints.main import main_bp
from app.blueprints.stats import stats_bp
from app.cli import register_commands
from app.config import Config
from app.database import init_db, shutdown_session
from app.i18n import TRANSLATIONS


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
    Config.check_configuration()
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24).hex())
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    # Initialize database
    init_db(app)

    # Initialize CSRF Protection
    CSRFProtect(app)

    @app.before_request
    def before_request():
        # Hardcode language to Dhivehi
        g.lang = "dv"

    app.teardown_appcontext(shutdown_session)

    @app.context_processor
    def inject_vars():
        # Get translations for current language
        lang = g.get("lang", "en")
        translations = TRANSLATIONS.get(lang, {})

        def _(key, **kwargs):
            return translations.get(key, key).format(**kwargs)

        return {"_": _, "translations": translations}

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(stats_bp, url_prefix="/stats")

    # Register CLI commands
    register_commands(app)

    return app
