import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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

from app.database import db_session
from app.llm_clients import get_available_models
from app.models import User
from app.predefined_queries import PREDEFINED_QUERIES
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

    available_models = get_available_models()
    usage_stats = get_model_usage_stats()

    # Sort models by usage count (ascending) to prefer those with fewer data points
    # If a model is not in usage_stats, count is 0
    sorted_models = sorted(available_models.keys(), key=lambda m: usage_stats.get(m, 0))

    # Select top 6 models
    selected_model_keys = sorted_models[:6]

    # Create the dictionary for selected models
    selected_models_dict = {k: available_models[k] for k in selected_model_keys}

    # Shuffle the display order
    keys_shuffled = list(selected_models_dict.keys())
    random.shuffle(keys_shuffled)
    final_models = {k: selected_models_dict[k] for k in keys_shuffled}

    return render_template(
        "index.html",
        predefined_queries=shuffled_queries,
        username=username,
        available_models=final_models,
    )


@main_bp.route("/get_available_models")
def available_models():
    """Returns a list of available (active) models for selection, limited to 6 for the UI."""
    available_models = get_available_models()
    usage_stats = get_model_usage_stats()

    sorted_models = sorted(available_models.keys(), key=lambda m: usage_stats.get(m, 0))

    selected_model_keys = sorted_models[:6]
    selected_models_dict = {k: available_models[k] for k in selected_model_keys}

    return jsonify({"models": selected_models_dict})


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

        for future in as_completed(futures):
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
            finally:
                time.sleep(0.1)

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

    return Response(
        stream_with_context(stream_translation_generator(query_text, selected_models)),
        mimetype="text/event-stream",
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


@main_bp.route("/set_language/<lang>")
def set_language(lang):
    """Set the language for the user session."""
    if lang in ["en", "dv"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("main.index"))
