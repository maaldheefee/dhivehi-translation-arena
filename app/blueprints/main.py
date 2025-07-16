import functools
import random

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    session,
)

from app.database import db_session
from app.llm_clients import TranslationClient
from app.models import User
from app.predefined_queries import PREDEFINED_QUERIES
from app.services.translation_service import get_translations

main_bp = Blueprint("main", __name__)


class TranslationCache:
    def __init__(self):
        self.cache = {}

    def init_app(self, app):
        """Initialize the cache with the app context."""
        self.MAX_CACHE_SIZE = app.config.get("MAX_CACHE_SIZE", 50)

    def clear(self):
        self.cache = {}
        current_app.logger.info("Translation cache cleared")
        return len(self.cache)

    def cache_translation(self, func):
        @functools.wraps(func)
        def wrapper(query_text, system_prompt):
            cache_key = f"{query_text}:{system_prompt}"

            if cache_key in self.cache:
                current_app.logger.info(f"Cache hit for: {cache_key}")
                return self.cache[cache_key]

            result = func(query_text, system_prompt)

            if len(self.cache) >= self.MAX_CACHE_SIZE:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]

            self.cache[cache_key] = result
            current_app.logger.info(f"Cached result for: {cache_key}")

            return result

        return wrapper


translation_cache = TranslationCache()


@main_bp.route("/")
def index():
    """Renders the main page with a shuffled list of predefined queries."""
    username = session.get("username", "Guest")
    shuffled_queries = PREDEFINED_QUERIES.copy()
    random.shuffle(shuffled_queries)
    return render_template(
        "index.html", predefined_queries=shuffled_queries, username=username
    )


@main_bp.route("/translate", methods=["POST"])
def translate():
    """
    Handles the translation request.
    Uses the translation service to get translations from multiple models.
    """
    data = request.json
    if data is None:
        return jsonify({"error": "No data provided"}), 400

    query_text = data.get("query", "").strip()
    if not query_text:
        return jsonify({"error": "No query provided"}), 400

    username = session.get("username", "Guest")

    # Check cache
    cache_key = f"{query_text}:{TranslationClient.SYSTEM_PROMPT}"
    if cache_key in translation_cache.cache:
        current_app.logger.info(f"Cache hit for translation: {cache_key}")
        cached_response = translation_cache.cache[cache_key].copy()
        return jsonify(cached_response)

    # Use translation service
    try:
        result = get_translations(query_text, username)

        response_data = {
            "query": query_text,
            "query_id": result["query_id"],
            "translations": [
                {
                    "id": t["id"],
                    "position": t["position"],
                    "translation": t["translation"],
                    "cost": t["cost"],
                    "model": t["model"],
                }
                for t in result["translations"]
            ],
            "voted_translation": result["voted_translation"],
        }

        translation_cache.cache[cache_key] = response_data
        return jsonify(response_data)

    except Exception:
        current_app.logger.exception("Error during translation")
        return jsonify({"error": "Translation service error"}), 500


@main_bp.route("/vote", methods=["POST"])
def vote():
    """Handles voting for translations using the star-rating voting system."""
    from app.services.vote_service import process_votes

    data = request.json
    query_id = data.get("query_id")
    votes = data.get("votes", [])
    username = session.get("username", "Guest")

    if not query_id:
        return jsonify({"error": "Missing query ID"}), 400

    if not votes:
        return jsonify({"error": "No votes provided"}), 400

    # Get user ID from username
    user = db_session.query(User).filter(User.username == username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Process the votes
    result = process_votes(user.id, query_id, votes)

    if result["success"]:
        return jsonify({"status": "success"})
    return jsonify({"error": result["error"]}), 500
