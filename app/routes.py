import functools
import hashlib
import random
import uuid

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    session,
)
from sqlalchemy import create_engine, desc, func, inspect

from app.llm_clients import TranslationClient, get_translation_client
from app.models import Base, Query, Translation, User, Vote
from app.predefined_queries import PREDEFINED_QUERIES

main = Blueprint("main", __name__)


class TranslationCache:
    def __init__(self):
        self.cache = {}
        self.MAX_CACHE_SIZE = 100

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


# Default users to create if none exist
DEFAULT_USERS = [
    {"username": "Hassaan", "password": "1234", "is_admin": True},
    {"username": "Ashraaf", "password": "1234", "is_admin": False},
]


def hash_password(password):
    """Create a simple hash of the password"""
    return hashlib.sha256(password.encode()).hexdigest()


def init_default_users(db_session):
    """Initialize default users if none exist"""
    user_count = db_session.query(User).count()
    if user_count == 0:
        for user_data in DEFAULT_USERS:
            user = User(
                username=user_data["username"],
                password_hash=hash_password(user_data["password"]),
                is_admin=user_data["is_admin"],
            )
            db_session.add(user)
        db_session.commit()
        current_app.logger.info("Default users created")


@main.before_request
def before_request():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

    if "username" not in session:
        session["username"] = "Guest"

    if request.endpoint not in ["static"]:
        db = current_app.db_session
        init_default_users(db)


@main.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    db = current_app.db_session
    user = db.query(User).filter(User.username == username).first()

    if not user or user.password_hash != hash_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    # Store the username in the session
    session["username"] = username
    session.permanent = True

    return jsonify({"success": True, "username": username})


@main.route("/get_users", methods=["GET"])
def get_users():
    db = current_app.db_session
    users = db.query(User).all()

    return jsonify(
        {
            "users": [
                {"username": user.username, "is_admin": user.is_admin} for user in users
            ]
        }
    )


@main.route("/add_user", methods=["POST"])
def add_user():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    is_admin = data.get("is_admin", False)

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    db = current_app.db_session

    # Check if user already exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return jsonify({"error": "Username already exists"}), 400

    # Create new user
    user = User(
        username=username, password_hash=hash_password(password), is_admin=is_admin
    )
    db.add(user)
    db.commit()

    return jsonify({"success": True, "username": username})


@main.route("/")
def index():
    # Get predefined queries for display
    username = session.get("username", "Guest")
    shuffled_queries = PREDEFINED_QUERIES.copy()
    random.shuffle(shuffled_queries)
    return render_template(
        "index.html", predefined_queries=shuffled_queries, username=username
    )


@main.route("/select_user", methods=["POST"])
def select_user():
    data = request.json
    username = data.get("username")

    if not username or username not in ["Hassaan", "Ashraaf"]:
        return jsonify({"error": "Invalid username"}), 400

    # Store the username in the session
    session["username"] = username
    session.permanent = True

    return jsonify({"success": True, "username": username})


@main.route("/translate", methods=["POST"])
def translate():
    data = request.json
    query_text = data.get("query", "").strip()

    if not query_text:
        return jsonify({"error": "No query provided"}), 400

    cache_key = f"{query_text}:{TranslationClient.SYSTEM_PROMPT}"
    if cache_key in translation_cache.cache:
        current_app.logger.info(f"Cache hit for translation: {cache_key}")

        # Return a copy of the cached data to avoid accidental modification
        cached_response = translation_cache.cache[cache_key].copy()

        # Update the voted_translation for the current user
        username = session.get("username", "Guest")
        db = current_app.db_session

        # Find the query ID from the first translation in the *cached* response
        if (
            cached_response.get("translations")
            and len(cached_response["translations"]) > 0
        ):
            first_translation_id = cached_response["translations"][0]["id"]
            # Fetch the *database* record for this translation
            translation = db.query(Translation).get(first_translation_id)

            if translation:
                # Check if the user has voted for this query in the *database*
                vote = (
                    db.query(Vote)
                    .join(Translation)
                    .filter(
                        Translation.query_id == translation.query_id,
                        Vote.user == username,
                    )
                    .first()
                )

                # Update the *cached* response with vote information
                if vote:
                    cached_response["voted_translation"] = vote.translation_id
                else:
                    cached_response["voted_translation"] = None
        else:
            # Handle edge case: cached response has no translations
            cached_response["voted_translation"] = None

        return jsonify(cached_response)

    # Initialize the database if it doesn't exist
    engine = create_engine(current_app.config["DATABASE_URI"])
    current_app.logger.info(f"Database URI: {current_app.config['DATABASE_URI']}")
    try:
        # Attempt to open and close a connection to check db
        conn = engine.connect()
        current_app.logger.info("Successfully opened a connection")
        conn.close()
        current_app.logger.info("Successfully closed the connection")
    except Exception:
        current_app.logger.exception("Error with database connection.")
        return jsonify({"error": "Database connection error"}), 500

    if not inspect(engine).has_table("queries"):
        Base.metadata.create_all(engine)

    db = current_app.db_session

    # Check if this is a predefined query
    is_predefined = 1 if query_text in PREDEFINED_QUERIES else 0

    # Check if this query already exists in the database
    query = db.query(Query).filter(Query.text == query_text).first()
    if not query:
        query = Query(text=query_text, is_predefined=is_predefined)
        db.add(query)
        db.commit()

    # Get the models and create a mapping for blind testing
    models = ["gemini-flash", "gemini-pro", "sonnet"]
    random.shuffle(models)  # Randomize the order for blind testing

    # Perform translations
    translations = []
    for i, model in enumerate(models, 1):
        # Check if this translation already exists in the *database*
        existing = (
            db.query(Translation)
            .filter(Translation.query_id == query.id, Translation.model == model)
            .first()
        )

        if existing:
            translations.append(
                {
                    "id": existing.id,
                    "model": model,  # Store model name for later reveal
                    "position": i,
                    "translation": existing.translation,
                    "cost": existing.cost,
                }
            )
        else:
            # Get the translation from the API
            client = get_translation_client(model)
            try:
                result, cost = client.translate(
                    query_text
                )  # Use the client's translate method
            except Exception:
                current_app.logger.exception(f"Error during translation with {model}.")
                return jsonify({"error": f"Translation failed for model {model}"}), 500

            # Save the translation to the *database*
            translation = Translation(
                query_id=query.id,
                model=model,
                translation=result,
                system_prompt=client.SYSTEM_PROMPT,  # Store for record-keeping
                position=i,
                cost=cost,
            )
            db.add(translation)
            try:
                db.commit()
            except Exception:
                db.rollback()
                current_app.logger.exception("Error saving translation to database.")
                return jsonify({"error": "Failed to save translation"}), 500

            translations.append(
                {
                    "id": translation.id,
                    "model": model,
                    "position": i,
                    "translation": result,
                    "cost": cost,
                }
            )

    # Sort translations by position for display
    translations = sorted(translations, key=lambda x: x["position"])

    # Get existing votes for this user and query from the *database*
    username = session.get("username", "Guest")
    voted_translation = None
    if username:
        vote = (
            db.query(Vote)
            .join(Translation)
            .filter(Translation.query_id == query.id, Vote.user == username)
            .first()
        )

        if vote:
            voted_translation = vote.translation_id

    # Construct the response data
    response_data = {
        "query": query_text,
        "translations": [
            {
                "id": t["id"],
                "position": t["position"],
                "translation": t["translation"],
                "cost": t["cost"],
                "model": t["model"],  # Include model name in response
            }
            for t in translations
        ],
        "voted_translation": voted_translation,
    }

    # Cache the response, using the consistent key
    translation_cache.cache[cache_key] = response_data

    return jsonify(response_data)


@main.route("/vote", methods=["POST"])
def vote():
    data = request.json
    translation_id = data.get("translation_id")
    username = session.get("username", "Guest")

    if not translation_id:
        return jsonify({"error": "Missing translation ID"}), 400

    db = current_app.db_session

    # Get the translation
    translation = db.query(Translation).get(translation_id)
    if not translation:
        return jsonify({"error": "Translation not found"}), 404

    # Check if the user has already voted for a translation of this query
    existing_vote = (
        db.query(Vote)
        .join(Translation)
        .filter(Translation.query_id == translation.query_id, Vote.user == username)
        .first()
    )

    if existing_vote:
        # Update existing vote
        existing_vote.translation_id = translation_id
    else:
        # Create new vote
        vote = Vote(translation_id=translation_id, user=username)
        db.add(vote)

    db.commit()

    # Return the model name along with success status
    return jsonify({"success": True, "model": translation.model})


@main.route("/clear_cache", methods=["POST"])
def clear_cache():
    """Clear the translation cache"""
    username = session.get("username", "Guest")
    db = current_app.db_session

    # Check if user is admin
    user = db.query(User).filter(User.username == username).first()
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


@main.route("/stats")
def stats():
    db = current_app.db_session
    username = session.get("username", "Guest")

    # Get vote counts by model
    votes_by_model = (
        db.query(Translation.model, func.count(Vote.id).label("vote_count"))
        .join(Vote)
        .group_by(Translation.model)
        .all()
    )

    # Get cost by model
    cost_by_model = (
        db.query(Translation.model, func.sum(Translation.cost).label("total_cost"))
        .group_by(Translation.model)
        .all()
    )

    # Get vote counts by user
    votes_by_user = (
        db.query(Vote.user, func.count(Vote.id).label("vote_count"))
        .group_by(Vote.user)
        .all()
    )

    # Get recent translations
    recent_translations = (
        db.query(
            Query.text,
            Translation.model,
            Translation.translation,
            func.count(Vote.id).label("vote_count"),
        )
        .select_from(Query)
        .join(Translation, Query.id == Translation.query_id)
        .outerjoin(Vote, Translation.id == Vote.translation_id)
        .group_by(Query.id, Translation.id)
        .order_by(desc(Query.created_at))
        .limit(20)
        .all()
    )

    stats_data = {
        "votes_by_model": dict(votes_by_model),
        "cost_by_model": {model: round(cost, 6) for model, cost in cost_by_model},
        "votes_by_user": dict(votes_by_user),
        "recent_translations": [
            {"query": query, "model": model, "translation": translation, "votes": votes}
            for query, model, translation, votes in recent_translations
        ],
    }

    return render_template("stats.html", stats=stats_data, username=username)
