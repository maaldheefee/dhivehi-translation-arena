import logging
import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, g
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

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
    # Use a stable key for development to prevent session invalidation on reload
    if (
        os.environ.get("FLASK_DEBUG") == "1"
        or os.environ.get("FLASK_ENV") == "development"
    ):
        default_secret = "dev-secret-key-stable"
    else:
        default_secret = os.urandom(24).hex()

    app.config["SECRET_KEY"] = (
        os.environ.get("SECRET_KEY") or app.config.get("SECRET_KEY") or default_secret
    )
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    # Initialize database
    init_db(app)

    # Initialize CSRF Protection
    CSRFProtect(app)

    # Fix for running behind a proxy (Cloudflare, Nginx, etc.)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

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
