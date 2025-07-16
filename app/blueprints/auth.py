import uuid

from flask import Blueprint, jsonify, request, session

from app.database import db_session
from app.models import User
from app.services.user_service import check_password, create_user, get_user_by_username

auth_bp = Blueprint("auth", __name__)


def init_default_users(db_session):
    """Initialize default users if none exist - now handled by init_db.py"""
    # This function is now a no-op since default user creation is handled exclusively by init_db.py
    # Keeping it for backward compatibility but it does nothing
    pass


@auth_bp.before_request
def before_request():
    """Initializes session."""
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

    if "username" not in session:
        session["username"] = "Guest"

    # Default user initialization is now handled by init_db.py
    # init_default_users(db_session) - no longer needed


@auth_bp.route("/login", methods=["POST"])
def login():
    """Handles user login."""
    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = get_user_by_username(username)

    if not user or not check_password(user, password):
        return jsonify({"error": "Invalid username or password"}), 401

    session["username"] = username
    session.permanent = True

    return jsonify({"success": True, "username": username})


@auth_bp.route("/get_users", methods=["GET"])
def get_users():
    """Returns a list of all users."""
    users = db_session.query(User).all()

    return jsonify(
        {
            "users": [
                {"username": user.username, "is_admin": user.is_admin} for user in users
            ]
        }
    )


@auth_bp.route("/add_user", methods=["POST"])
def add_user():
    """Adds a new user to the database."""
    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username")
    password = data.get("password")
    is_admin = data.get("is_admin", False)

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = create_user(username, password, is_admin)
    if not user:
        return jsonify({"error": "Username already exists"}), 400

    return jsonify({"success": True, "username": username})


@auth_bp.route("/select_user", methods=["POST"])
def select_user():
    """Allows selecting a user without a password (for demo purposes)."""
    data = request.json
    username = data.get("username")

    # This is an insecure way to switch users, for demo only.
    if not username:
        return jsonify({"error": "Invalid username"}), 400

    session["username"] = username
    session.permanent = True

    return jsonify({"success": True, "username": username})
