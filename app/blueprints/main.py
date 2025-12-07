import json
import random
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from itertools import combinations

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)
from sqlalchemy import func

from app.config import get_config
from app.database import db_session
from app.llm_clients import get_available_models
from app.models import PairwiseComparison, Query, Translation, User
from app.predefined_queries import PREDEFINED_QUERIES
from app.services.elo_service import get_elo_service
from app.services.stats_service import get_model_usage_stats
from app.services.translation_service import get_translation_for_model
from app.services.vote_service import process_votes

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Renders the main page with a shuffled list of predefined queries."""
    username = session.get("username", "Guest")
    shuffled_queries = PREDEFINED_QUERIES.copy()
    random.shuffle(shuffled_queries)
    shuffled_queries = shuffled_queries[:10]

    available_models = get_available_models()
    usage_stats = get_model_usage_stats()


    # Sort models by usage count (ascending) to prefer those with fewer data points
    # If a model is not in usage_stats, count is 0
    sorted_model_keys = sorted(available_models.keys(), key=lambda m: usage_stats.get(m, 0))

    # Create the dictionary for all models in sorted order
    final_models = {k: available_models[k] for k in sorted_model_keys}

    # Shuffle the display order of all models
    keys_shuffled = list(final_models.keys())
    random.shuffle(keys_shuffled)
    final_models_shuffled = {k: final_models[k] for k in keys_shuffled}

    return render_template(
        "index.html",
        predefined_queries=shuffled_queries,
        username=username,
        available_models=final_models_shuffled,
    )


@main_bp.route("/get_available_models")
def available_models():
    """Returns a list of available (active) models for selection."""
    available_models = get_available_models()
    usage_stats = get_model_usage_stats()

    sorted_model_keys = sorted(available_models.keys(), key=lambda m: usage_stats.get(m, 0))

    # Return all models, sorted by usage
    sorted_models_dict = {k: available_models[k] for k in sorted_model_keys}

    return jsonify({"models": sorted_models_dict})


def stream_translation_generator(query_text, selected_models):
    """
    A generator function that yields translation results as they are completed.
    This function will be used with stream_with_context.
    """
    shuffled_models = random.sample(selected_models, len(selected_models))
    futures = {}

    with ThreadPoolExecutor(max_workers=len(shuffled_models)) as executor:
        for i, model_key in enumerate(shuffled_models):
            future = executor.submit(
                get_translation_for_model, query_text, model_key, i + 1
            )
            futures[future] = model_key

        pending_futures = set(futures.keys())
        while pending_futures:
            # Wait for any future to complete, or timeout after 2 seconds
            done, _ = wait(pending_futures, return_when=FIRST_COMPLETED, timeout=2.0)

            if not done:
                # No model finished in the last 2 seconds, send keep-alive comment
                yield ": keep-alive\n\n"
                continue

            for future in done:
                pending_futures.remove(future)
                model_key = futures[future]
                try:
                    result = future.result()
                    if result:
                        sse_data = f"data: {json.dumps(result)}\n\n"
                        yield sse_data
                except Exception as e:
                    current_app.logger.exception(f"Stream error for {model_key}")
                    error_data = {"error": str(e), "model": model_key}
                    yield f"data: {json.dumps(error_data)}\n\n"

    yield "event: end\ndata: Stream finished\n\n"


@main_bp.route("/stream-translate")
def stream_translate():
    """
    Handles the translation request by streaming results as they are ready.
    """
    query_text = request.args.get("query", "").strip()
    selected_models = request.args.getlist("models")

    if not query_text or not selected_models or len(selected_models) < 2:
        error_event = f"event: error\ndata: {json.dumps({'message': 'Query and at least two models are required.'})}\n\n"
        return Response(error_event, mimetype="text/event-stream")

    username = session.get("username", "Guest")
    if username == "Guest":
        error_data = {"message": "Authentication required", "type": "auth_error"}
        error_event = f"event: error\ndata: {json.dumps(error_data)}\n\n"
        return Response(error_event, mimetype="text/event-stream")

    return Response(
        stream_with_context(stream_translation_generator(query_text, selected_models)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@main_bp.route("/vote", methods=["POST"])
def vote():
    """Handles voting for translations using the star-rating voting system."""
    data = request.json
    if data is None:
        return jsonify({"error": "Invalid JSON data"}), 400
    query_id = data.get("query_id")
    votes = data.get("votes", [])
    username = session.get("username", "Guest")

    if not query_id or not votes:
        return jsonify({"error": "Missing query ID or votes"}), 400

    user = db_session.query(User).filter(User.username == username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    result = process_votes(user.id, query_id, votes)

    if result["success"]:
        return jsonify({"status": "success"})
    return jsonify({"error": result["error"]}), 500


@main_bp.route("/retry-single", methods=["POST"])
def retry_single():
    """Retry a single model translation. Returns JSON instead of SSE."""
    username = session.get("username", "Guest")
    if username == "Guest":
        return jsonify({"error": "Authentication required"}), 401

    data = request.json
    if data is None:
        return jsonify({"error": "Invalid JSON data"}), 400

    query_text = data.get("query", "").strip()
    model_key = data.get("model", "").strip()

    if not query_text or not model_key:
        return jsonify({"error": "Query and model are required"}), 400

    try:
        result = get_translation_for_model(query_text, model_key, position=0)
        if result:
            return jsonify(result)
        return jsonify({"error": "No result returned"}), 500
    except Exception as e:
        current_app.logger.exception(f"Retry failed for {model_key}")
        return jsonify({"error": str(e), "model": model_key}), 500


@main_bp.route("/set_language/<lang>")
def set_language(lang):
    """Set the language for the user session."""
    if lang in ["en", "dv"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("main.index"))


@main_bp.route("/compare")
def compare_ui():
    """Renders the pairwise comparison UI."""
    username = session.get("username", "Guest")
    return render_template("compare.html", username=username)


@main_bp.route("/compare/random")
def get_random_comparison():
    """
    Get 2 translations from the same query for pairwise comparison.
    Returns translations that haven't been compared yet or need more comparisons.
    """

    username = session.get("username", "Guest")
    user = db_session.query(User).filter(User.username == username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Find queries with at least 2 translations
    queries_with_translations = (
        db_session.query(Query.id)
        .join(Translation)
        .group_by(Query.id)
        .having(func.count(Translation.id) >= 2)
        .all()
    )

    if not queries_with_translations:
        return jsonify({"error": "No queries with multiple translations found"}), 404

    # Pick a random query
    query_ids = [q.id for q in queries_with_translations]
    random.shuffle(query_ids)

    for query_id in query_ids:
        translations = (
            db_session.query(Translation).filter(Translation.query_id == query_id).all()
        )

        if len(translations) < 2:
            continue

        # Find a pair that hasn't been compared by this user
        for t1, t2 in combinations(translations, 2):
            existing = (
                db_session.query(PairwiseComparison)
                .filter(
                    PairwiseComparison.user_id == user.id,
                    PairwiseComparison.translation_a_id == t1.id,
                    PairwiseComparison.translation_b_id == t2.id,
                    PairwiseComparison.source == "explicit",
                )
                .first()
            )
            if not existing:
                # Found a pair to compare
                query = db_session.query(Query).get(query_id)

                # Get model config info
                conf = get_config()

                t1_config = conf.MODELS.get(t1.model, {})
                t2_config = conf.MODELS.get(t2.model, {})

                return jsonify(
                    {
                        "query_id": query_id,
                        "source_text": query.source_text if query else "",
                        "translations": [
                            {
                                "id": t1.id,
                                "text": t1.translation,
                                "model": t1.model,
                                "base_model": t1_config.get("base_model", t1.model),
                                "preset_name": t1_config.get("preset_name"),
                            },
                            {
                                "id": t2.id,
                                "text": t2.translation,
                                "model": t2.model,
                                "base_model": t2_config.get("base_model", t2.model),
                                "preset_name": t2_config.get("preset_name"),
                            },
                        ],
                    }
                )

    return jsonify({"error": "All pairs have been compared"}), 404


@main_bp.route("/compare/submit", methods=["POST"])
def submit_comparison():
    """
    Record a pairwise comparison result.

    Expected JSON body:
    {
        "query_id": int,
        "winner_id": int | null,  // translation ID of winner, null for tie
        "translation_ids": [int, int]  // the two translations being compared
    }
    """

    data = request.json
    if data is None:
        return jsonify({"error": "Invalid JSON data"}), 400

    query_id = data.get("query_id")
    winner_id = data.get("winner_id")  # Can be None for tie
    translation_ids = data.get("translation_ids", [])

    if not query_id or len(translation_ids) != 2:
        return jsonify({"error": "Missing query_id or translation_ids"}), 400

    username = session.get("username", "Guest")
    user = db_session.query(User).filter(User.username == username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Get translations
    t1 = db_session.query(Translation).get(translation_ids[0])
    t2 = db_session.query(Translation).get(translation_ids[1])

    if not t1 or not t2:
        return jsonify({"error": "Translations not found"}), 404

    # Determine winner/loser
    winner_model = None
    loser_model = None
    if winner_id:
        if winner_id == t1.id:
            winner_model = t1.model
            loser_model = t2.model
        elif winner_id == t2.id:
            winner_model = t2.model
            loser_model = t1.model
        else:
            return jsonify({"error": "winner_id must be one of translation_ids"}), 400

    try:
        elo_service = get_elo_service()
        elo_service.record_comparison(
            query_id=query_id,
            user_id=user.id,
            winner_model=winner_model,
            loser_model=loser_model,
            translation_a_id=t1.id,
            translation_b_id=t2.id,
            source="explicit",
        )
        return jsonify({"status": "success"})
    except Exception as e:
        current_app.logger.exception("Error recording comparison")
        return jsonify({"error": str(e)}), 500
