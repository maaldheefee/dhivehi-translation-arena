import os

from dotenv import load_dotenv
from datetime import timedelta

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Load environment variables
load_dotenv()


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # Configure the app
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24).hex())
    app.config["DATABASE_URI"] = "sqlite:///data/translations.db"
    app.config["CACHE_DATABASE_URI"] = (
        "sqlite:///data/cache.db"  # Separate cache database
    )
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    # Set up main database
    engine = create_engine(app.config["DATABASE_URI"])
    app.db_session = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )

    # Set up cache database (will be used in future implementation)
    cache_engine = create_engine(app.config["CACHE_DATABASE_URI"])
    app.cache_db_session = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=cache_engine)
    )

    # Import and register blueprints
    from app.routes import main

    app.register_blueprint(main)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        app.db_session.remove()
        app.cache_db_session.remove()  # Also remove cache session

    return app
