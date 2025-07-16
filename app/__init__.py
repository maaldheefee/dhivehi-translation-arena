import logging
import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask

from app.blueprints.admin import admin_bp
from app.blueprints.auth import auth_bp
from app.blueprints.main import main_bp, translation_cache
from app.blueprints.stats import stats_bp
from app.database import teardown_db_session

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # Configure the app
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24).hex())
    app.config["DATABASE_URI"] = "sqlite:///data/translations.db"
    app.config["CACHE_DATABASE_URI"] = (
        "sqlite:///data/cache.db"  # Separate cache database
    )
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(stats_bp)

    # Initialize cache
    translation_cache.init_app(app)

    # Register teardown function
    app.teardown_appcontext(teardown_db_session)

    return app
