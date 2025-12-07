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
from app.services.cost_service import check_user_budget
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

    # Get user budget info
    is_allowed, user_monthly_cost = check_user_budget(username)

    # Sort models by usage count (ascending) to prefer those with fewer data points
    # If a model is not in usage_stats, count is 0
    sorted_model_keys = sorted(
        available_models.keys(), key=lambda m: usage_stats.get(m, 0)
    )

    # Limit to MAX_MODELS_SELECTION (prioritizing those with fewest data points)
    max_models = get_config().MAX_MODELS_SELECTION
    selected_model_keys = sorted_model_keys[:max_models]

    # Create the dictionary for only the selected models
    final_models = {k: available_models[k] for k in selected_model_keys}

    # Shuffle the display order of the selected models
    keys_shuffled = list(final_models.keys())
    random.shuffle(keys_shuffled)
    final_models_shuffled = {k: final_models[k] for k in keys_shuffled}

    return render_template(
        "index.html",
        predefined_queries=shuffled_queries,
        username=username,
        available_models=final_models_shuffled,
        user_monthly_cost=user_monthly_cost,
        budget_allowed=is_allowed,
    )


@main_bp.route("/get_available_models")
def available_models():
    """Returns a list of available (active) models for selection."""
    available_models = get_available_models()
    usage_stats = get_model_usage_stats()

    sorted_model_keys = sorted(
        available_models.keys(), key=lambda m: usage_stats.get(m, 0)
    )

    # Return all models, sorted by usage
    sorted_models_dict = {k: available_models[k] for k in sorted_model_keys}

    return jsonify({"models": sorted_models_dict})


def stream_translation_generator(query_text, selected_models, user_id=None):
    """
    A generator function that yields translation results as they are completed.
    This function will be used with stream_with_context.
    """
    shuffled_models = random.sample(selected_models, len(selected_models))
    futures = {}

    with ThreadPoolExecutor(max_workers=len(shuffled_models)) as executor:
        for i, model_key in enumerate(shuffled_models):
            future = executor.submit(
                get_translation_for_model, query_text, model_key, i + 1, user_id
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

    # Check budget
    is_allowed, current_spend = check_user_budget(username)
    if not is_allowed:
        error_data = {
            "message": f"Monthly budget exceeded (${current_spend:.2f}/$1.00). Please wait until next month.",
            "type": "budget_error",
        }
        error_event = f"event: error\ndata: {json.dumps(error_data)}\n\n"
        return Response(error_event, mimetype="text/event-stream")

    # Get user ID for cost tracking
    user = db_session.query(User).filter(User.username == username).first()
    user_id = user.id if user else None

    return Response(
        stream_with_context(
            stream_translation_generator(query_text, selected_models, user_id)
        ),
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

    # Check budget
    is_allowed, current_spend = check_user_budget(username)
    if not is_allowed:
        return jsonify(
            {"error": f"Monthly budget exceeded (${current_spend:.2f}/$1.00)"}
        ), 403

    data = request.json
    if data is None:
        return jsonify({"error": "Invalid JSON data"}), 400

    query_text = data.get("query", "").strip()
    model_key = data.get("model", "").strip()

    if not query_text or not model_key:
        return jsonify({"error": "Query and model are required"}), 400

    # Get user ID for cost tracking
    user = db_session.query(User).filter(User.username == username).first()
    user_id = user.id if user else None

    try:
        result = get_translation_for_model(
            query_text, model_key, position=0, user_id=user_id
        )
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

    # Optimize: Fetch all model ELOs once
    elo_service = get_elo_service()
    all_elos = {r["model"]: r["elo_rating"] for r in elo_service.get_all_rankings()}

    # Optimize: Get user's existing comparisons for checking (could be large, so maybe filter by query later if needed)
    # Actually, better to fetch per query to avoid massive memory usage if user has done 1000s.
    for query_id in query_ids:
        translations = (
            db_session.query(Translation).filter(Translation.query_id == query_id).all()
        )

        if len(translations) < 2:
            continue

        # --- Filter Candidates ---
        # 1. Reject explicit trash (optional, if we track rejection status on Translation)
        # 2. Reject if average vote < 1.5 (requires joining votes, maybe expensive here)
        # For now, we trust the "model sorting" to naturally deprioritize bad models if we selected good ones upstream.

        # Optimize: Fetch ALL existing comparisons for this query by this user in ONE query
        # This replaces the N*N loop of DB calls
        existing_pairs = (
            db_session.query(
                PairwiseComparison.translation_a_id, PairwiseComparison.translation_b_id
            )
            .filter(
                PairwiseComparison.user_id == user.id,
                PairwiseComparison.query_id == query_id,
                PairwiseComparison.source == "explicit",
            )
            .all()
        )
        # Create a set of frozen sets for order-independent lookup: {(id1, id2), ...}
        compared_pairs = {frozenset([p[0], p[1]]) for p in existing_pairs}

        candidate_pairs = []

        # Shuffle translations first to ensure random tie-breaking
        random.shuffle(translations)

        for t1, t2 in combinations(translations, 2):
            pair_key = frozenset([t1.id, t2.id])
            if pair_key in compared_pairs:
                continue

            # Calculate ELO difference
            elo1 = all_elos.get(t1.model, 1500.0)
            elo2 = all_elos.get(t2.model, 1500.0)
            diff = abs(elo1 - elo2)

            candidate_pairs.append(((t1, t2), diff))

        if candidate_pairs:
            # Sort by ELO difference (ascending) -> compare closest models first
            # Add noise to the sort key? No, easier to just pick random from top N.
            candidate_pairs.sort(key=lambda x: x[1])

            # Take top 5 closest pairs and pick one randomly
            top_candidates = candidate_pairs[:5]
            selected_pair, _ = random.choice(top_candidates)
            t1, t2 = selected_pair

            # Found a pair!
            query = db_session.query(Query).get(query_id)
            conf = get_config()

            # Stats Calculation
            stats = _get_user_comparison_stats(user.id)

            return jsonify(
                {
                    "query_id": query_id,
                    "source_text": query.source_text if query else "",
                    "translations": [
                        {
                            "id": t1.id,
                            "text": t1.translation,
                            "model": t1.model,
                            "base_model": conf.MODELS.get(t1.model, {}).get(
                                "base_model", t1.model
                            ),
                            "preset_name": conf.MODELS.get(t1.model, {}).get(
                                "preset_name"
                            ),
                        },
                        {
                            "id": t2.id,
                            "text": t2.translation,
                            "model": t2.model,
                            "base_model": conf.MODELS.get(t2.model, {}).get(
                                "base_model", t2.model
                            ),
                            "preset_name": conf.MODELS.get(t2.model, {}).get(
                                "preset_name"
                            ),
                        },
                    ],
                    "stats": stats,
                }
            )

    return jsonify({"error": "All pairs have been compared"}), 404


def _get_user_comparison_stats(user_id):
    """Helper to calculate user comparison stats efficiently."""
    # 1. Count user's explicit comparisons
    comparisons_count = (
        db_session.query(func.count(PairwiseComparison.id))
        .filter(
            PairwiseComparison.user_id == user_id,
            PairwiseComparison.source == "explicit",
        )
        .scalar()
    ) or 0

    # 2. Estimate total pairs
    # OPTIMIZATION: This aggregation is heavy.
    # In a real app, we might cache this value or update it incrementally.
    # For now, we'll keep it but ensure we use indices.
    # Note: query(Translation.query_id, count(*)) is still a full table scan usually unless indexed on query_id
    translation_counts = (
        db_session.query(func.count(Translation.id))
        .group_by(Translation.query_id)
        .having(func.count(Translation.id) >= 2)
        .all()
    )

    total_pairs = sum((c[0] * (c[0] - 1)) // 2 for c in translation_counts)
    pairs_remaining = max(0, total_pairs - comparisons_count)

    return {
        "comparisons_done": comparisons_count,
        "pairs_remaining": pairs_remaining,
        "total_pairs": total_pairs,
    }

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
