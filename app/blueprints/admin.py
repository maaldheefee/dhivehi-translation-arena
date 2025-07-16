from flask import Blueprint, jsonify, session

from app.database import db_session
from app.models import User

from .main import translation_cache

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/clear_cache", methods=["POST"])
def clear_cache():
    """Clear the translation cache"""
    username = session.get("username", "Guest")

    # Check if user is admin
    user = db_session.query(User).filter(User.username == username).first()
    if not user or not user.is_admin:
        return jsonify({"error": "Unauthorized. Admin access required."}), 403

    # Clear the cache
    items_cleared = translation_cache.clear()

    return jsonify(
        {
            "success": True,
            "message": f"Cache cleared successfully. {items_cleared} items removed.",
        }
    )
