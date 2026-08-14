import json
import random
import time
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

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
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import aliased
from werkzeug.wrappers import Response as WerkzeugResponse

from app.config import Config, get_config
from app.database import db_session
from app.decorators import login_required
from app.llm_clients import get_available_models
from app.models import PairwiseComparison, Query, Translation, User, Vote
from app.predefined_queries import PREDEFINED_QUERIES
from app.services.cost_service import check_user_budget
from app.services.elo_service import get_elo_service
from app.services.acquisition_policy import ModelCandidate, select_burst_models
from app.services.stats_service import (
    get_model_usage_stats,
    get_pair_comparison_counts,
    get_query_difficulty,
    invalidate_caches,
)
from app.services.translation_service import get_translation_for_model
from app.services.vote_service import process_votes

main_bp = Blueprint("main", __name__)


def _select_models(
    available_models_map: dict[str, str],
    usage_stats: dict[str, int],
    config: Config,
    max_models: int | None = None,
    excluded_models: set[str] | None = None,
    rating_deviations: dict[str, float] | None = None,
):
    """
    Selects up to MAX_MODELS models with balanced randomness and strategic grouping.

    Main objective:
    - Random selection of models limited to MAX_MODELS

    Secondary objectives:
    - Prioritize models with low usage/votes to build up data evenly
    - Group preset variants of the same base model together (e.g., thinking vs no-thinking,
      high temp vs low temp) to enable quality ELO comparisons between configurations

    Algorithm:
    1. Group models by base_model
    2. Calculate average usage per group (to prioritize low-usage groups)
    3. Shuffle groups with similar usage to add randomness
    4. Select groups in priority order, including all variants from each group
    5. Stop when we would exceed MAX_MODELS
    """
    max_models = max_models if max_models is not None else config.MAX_MODELS_SELECTION
    excluded_models = excluded_models or set()

    if rating_deviations is not None:
        candidates = [
            ModelCandidate(
                key=key,
                base_model=config.MODELS.get(key, {}).get("base_model", key),
                usage=usage_stats.get(key, 0),
                rating_deviation=rating_deviations.get(key, config.GLICKO_INITIAL_RD),
                output_cost=config.MODELS.get(key, {}).get("output_cost_per_mtok", 0.0),
            )
            for key in available_models_map
            if key not in excluded_models
        ]
        return select_burst_models(
            candidates,
            max_models,
            config.COST_MID_MAX,
            config.MAX_EXPENSIVE_GROUPS,
        )

    # Group models by base_model
    base_groups = defaultdict(list)
    for key in available_models_map:
        if key in excluded_models:
            continue
        base = config.MODELS.get(key, {}).get("base_model", key)
        base_groups[base].append(key)

    # Calculate average usage for each group (for prioritization)
    # Lower average = higher priority
    group_priorities = []
    for base, model_keys in base_groups.items():
        avg_usage = sum(usage_stats.get(k, 0) for k in model_keys) / len(model_keys)
        group_priorities.append((avg_usage, base, model_keys))

    # Sort by average usage (ascending = low usage first)
    group_priorities.sort(key=lambda x: x[0])

    # Add randomness: group by usage buckets and shuffle within buckets
    # This prevents deterministic bias while still prioritizing low-usage models
    bucketed_groups = []
    current_bucket = []
    current_bucket_max = -1

    for avg_usage, base, model_keys in group_priorities:
        # Create buckets of groups with similar usage (within 5 votes of each other)
        if current_bucket_max < 0 or avg_usage <= current_bucket_max + 5:
            current_bucket.append((avg_usage, base, model_keys))
            current_bucket_max = max(current_bucket_max, avg_usage)
        else:
            # Shuffle current bucket and add to result
            random.shuffle(current_bucket)
            bucketed_groups.extend(current_bucket)
            # Start new bucket
            current_bucket = [(avg_usage, base, model_keys)]
            current_bucket_max = avg_usage

    # Don't forget the last bucket
    if current_bucket:
        random.shuffle(current_bucket)
        bucketed_groups.extend(current_bucket)

    # Select groups until we reach MAX_MODELS
    selected_keys = []
    for _, _base, model_keys in bucketed_groups:
        # Check if adding this entire group would exceed the limit
        if len(selected_keys) + len(model_keys) <= max_models:
            # Include all variants from this base model
            selected_keys.extend(model_keys)
        elif len(selected_keys) < max_models:
            # Partial selection: we have some room but not enough for all variants
            # Randomly select variants to fill remaining slots
            remaining_slots = max_models - len(selected_keys)
            # Sort variants by usage within this group, then take top N
            variants_by_usage = sorted(model_keys, key=lambda k: usage_stats.get(k, 0))
            selected_keys.extend(variants_by_usage[:remaining_slots])
            break
        else:
            # Already at capacity
            break

    # Cost-aware constraint: max MAX_EXPENSIVE_GROUPS expensive base model groups
    expensive_groups = []
    for key in selected_keys:
        base = config.MODELS.get(key, {}).get("base_model", key)
        output_cost = config.MODELS.get(key, {}).get("output_cost_per_mtok", 0.0)
        if output_cost > config.COST_MID_MAX and base not in expensive_groups:
            expensive_groups.append(base)

    if len(expensive_groups) > config.MAX_EXPENSIVE_GROUPS:
        # Keep only the first MAX_EXPENSIVE_GROUPS expensive groups (highest priority = lowest usage)
        allowed_expensive = set(expensive_groups[: config.MAX_EXPENSIVE_GROUPS])
        # Remove keys from disallowed expensive groups
        removed_keys = []
        for key in list(selected_keys):
            base = config.MODELS.get(key, {}).get("base_model", key)
            output_cost = config.MODELS.get(key, {}).get("output_cost_per_mtok", 0.0)
            if output_cost > config.COST_MID_MAX and base not in allowed_expensive:
                selected_keys.remove(key)
                removed_keys.append(key)

        # Backfill with cheap/mid models from remaining pool
        # (exclude all expensive models to avoid re-adding disallowed groups)
        remaining_pool = [
            k
            for k in available_models_map
            if k not in selected_keys
            and k not in excluded_models
            and config.MODELS.get(k, {}).get("output_cost_per_mtok", 0.0) <= config.COST_MID_MAX
        ]
        # Sort by usage (low first) and add back
        remaining_pool.sort(key=lambda k: usage_stats.get(k, 0))
        for key in remaining_pool:
            if len(selected_keys) >= max_models:
                break
            selected_keys.append(key)

    return selected_keys


@main_bp.route("/")
def index() -> str:
    """Renders the main page with stratified query selection and cost-aware model selection."""
    username = session.get("username", "Guest")
    conf = get_config()

    # Stratified query selection based on difficulty
    difficulty_map = get_query_difficulty()

    # Build query -> difficulty mapping (using source_text as key since PREDEFINED_QUERIES are strings)
    # Fetch Query IDs for predefined query texts
    query_rows = db_session.query(Query).filter(Query.source_text.in_(PREDEFINED_QUERIES)).all()
    text_to_id = {str(q.source_text): int(q.id) for q in query_rows}

    # Categorize predefined queries by difficulty tier
    tier_pools: dict[str, list[str]] = {
        "easy": [],
        "medium": [],
        "hard": [],
        "unknown": [],
    }
    for q_text in PREDEFINED_QUERIES:
        qid = text_to_id.get(q_text)
        tier = difficulty_map.get(qid, "unknown") if qid is not None else "unknown"
        tier_pools[tier].append(q_text)

    # Select queries per tier with backfill
    selected_queries: list[str] = []
    remaining: list[str] = []

    for tier, target_count in conf.STRATIFIED_TARGETS.items():
        pool = tier_pools.get(tier, [])
        random.shuffle(pool)
        take = min(target_count, len(pool))
        selected_queries.extend(pool[:take])
        remaining.extend(pool[take:])

    # Backfill to reach STRATIFIED_TOTAL from remaining pool
    shortfall = conf.STRATIFIED_TOTAL - len(selected_queries)
    if shortfall > 0 and remaining:
        random.shuffle(remaining)
        selected_queries.extend(remaining[:shortfall])

    # Shuffle final selection for display
    random.shuffle(selected_queries)

    available_models = get_available_models()
    usage_stats = get_model_usage_stats()

    # Get user budget info
    is_allowed, user_monthly_cost = check_user_budget(username)

    # Select models with smart grouping and cost-aware constraint
    rating_deviations = {item["model"]: item["rating_deviation"] for item in get_elo_service().get_all_rankings()}
    selected_model_keys = _select_models(available_models, usage_stats, conf, rating_deviations=rating_deviations)

    # Create the dictionary for only the selected models
    final_models = {k: available_models[k] for k in selected_model_keys}

    # Shuffle the display order of the selected models
    keys_shuffled = list(final_models.keys())
    random.shuffle(keys_shuffled)
    final_models_shuffled = {k: final_models[k] for k in keys_shuffled}

    return render_template(
        "index.html",
        predefined_queries=selected_queries,
        username=username,
        available_models=final_models_shuffled,
        user_monthly_cost=user_monthly_cost,
        budget_allowed=is_allowed,
    )


@main_bp.route("/get_available_models")
def available_models() -> Response:
    """Returns a list of available (active) models for selection."""
    available_models_map = get_available_models()
    usage_stats = get_model_usage_stats()
    conf = get_config()

    # Parse frontend parameters
    hidden_param = request.args.get("hidden", "")
    hidden_models = {m.strip() for m in hidden_param.split(",") if m.strip()}

    count_param = request.args.get("count")
    try:
        max_models = int(count_param) if count_param else None
        if max_models is not None:
            max_models = max(1, min(max_models, conf.MAX_MODELS_SELECTION))
    except (ValueError, TypeError):
        max_models = None

    # Use smart selection logic
    selected_keys = set(
        _select_models(
            available_models_map,
            usage_stats,
            conf,
            max_models=max_models,
            excluded_models=hidden_models,
        )
    )

    # Still sort the returned list by usage to show least used first
    sorted_model_keys = sorted(available_models_map.keys(), key=lambda m: usage_stats.get(m, 0))

    # Return models object with details
    models_data = {}

    for k in sorted_model_keys:
        model_conf = conf.MODELS.get(k, {})
        models_data[k] = {
            "name": available_models_map[k],
            "input_cost": model_conf.get("input_cost_per_mtok", 0),
            "output_cost": model_conf.get("output_cost_per_mtok", 0),
            "selected": k in selected_keys,
        }

    return jsonify({"models": models_data})


def stream_translation_generator(query_text: str, selected_models: list[str], user_id: int | None = None):
    """
    A generator function that yields translation results as they are completed.
    This function will be used with stream_with_context.
    """
    shuffled_models = random.sample(selected_models, len(selected_models))
    futures = {}
    max_duration = 180.0
    start_time = time.monotonic()

    with ThreadPoolExecutor(max_workers=len(shuffled_models)) as executor:
        for i, model_key in enumerate(shuffled_models):
            future = executor.submit(get_translation_for_model, query_text, model_key, i + 1, user_id)
            futures[future] = model_key

        pending_futures = set(futures.keys())
        while pending_futures:
            elapsed = time.monotonic() - start_time
            if elapsed >= max_duration:
                current_app.logger.warning(
                    "Stream timed out after %.0fs, cancelling %d pending futures",
                    elapsed,
                    len(pending_futures),
                )
                for f in pending_futures:
                    f.cancel()
                    error_data = {"error": "Translation timed out", "model": futures[f]}
                    yield f"data: {json.dumps(error_data)}\n\n"
                break

            remaining_timeout = max(2.0, max_duration - elapsed)
            done, _ = wait(
                pending_futures,
                return_when=FIRST_COMPLETED,
                timeout=min(2.0, remaining_timeout),
            )

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
                    current_app.logger.exception("Stream error for %s", model_key)
                    error_data = {"error": str(e), "model": model_key}
                    yield f"data: {json.dumps(error_data)}\n\n"

    yield "event: end\ndata: Stream finished\n\n"


@main_bp.route("/stream-translate")
def stream_translate() -> Response:
    """
    Handles the translation request by streaming results as they are ready.
    """
    query_text = request.args.get("query", "").strip()
    selected_models = request.args.getlist("models")

    if not query_text or not selected_models or len(selected_models) < 2:
        error_event = (
            f"event: error\ndata: {json.dumps({'message': 'Query and at least two models are required.'})}\n\n"
        )
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
    user_id = int(user.id) if user else None

    return Response(
        stream_with_context(stream_translation_generator(query_text, selected_models, user_id)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@main_bp.route("/vote", methods=["POST"])
def vote() -> Response | tuple[Response, int]:
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

    result = process_votes(int(user.id), query_id, votes)

    if result["success"]:
        return jsonify({"status": "success"})
    return jsonify({"error": result["error"]}), 500


@main_bp.route("/retry-single", methods=["POST"])
def retry_single() -> Response | tuple[Response, int]:
    """Retry a single model translation. Returns JSON instead of SSE."""
    username = session.get("username", "Guest")
    if username == "Guest":
        return jsonify({"error": "Authentication required"}), 401

    # Check budget
    is_allowed, current_spend = check_user_budget(username)
    if not is_allowed:
        return jsonify({"error": f"Monthly budget exceeded (${current_spend:.2f}/$1.00)"}), 403

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
            query_text,
            model_key,
            position=0,
            user_id=int(user_id) if user_id is not None else None,
        )
        if result:
            return jsonify(result)
        return jsonify({"error": "No result returned"}), 500
    except Exception as e:
        current_app.logger.exception("Retry failed for %s", model_key)
        return jsonify({"error": str(e), "model": model_key}), 500


@main_bp.route("/set_language/<lang>")
def set_language(lang) -> WerkzeugResponse:
    """Set the language for the user session."""
    if lang in ["en", "dv"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("main.index"))


@main_bp.route("/compare")
@login_required
def compare_ui() -> str:
    """Renders the pairwise comparison UI."""
    username = session.get("username", "Guest")
    return render_template("compare.html", username=username)


def _compute_pair_priority(
    elo_a: float,
    rd_a: float,
    elo_b: float,
    rd_b: float,
    pair_count: int,
    same_rating: bool,
) -> float:
    """Compute composite pair priority score.

    Weights: ELO closeness 30%, RD uncertainty 25%, pair hunger 25%,
    same-rated bonus +0.3 additive.
    """
    elo_diff = abs(elo_a - elo_b)
    elo_closeness = 1.0 / (1.0 + elo_diff / 100.0)

    avg_rd = (rd_a + rd_b) / 2.0
    uncertainty = min(1.0, avg_rd / 350.0)

    pair_hunger = 1.0 / (1.0 + pair_count)

    same_rated_bonus = 0.3 if same_rating else 0.0

    return elo_closeness * 0.30 + uncertainty * 0.25 + pair_hunger * 0.25 + same_rated_bonus


@main_bp.route("/compare/random")
@login_required
def get_random_comparison() -> Response | tuple[Response, int]:
    """
    Get 2 translations from the same query for pairwise comparison.
    Returns translations that haven't been compared yet or need more comparisons.

    Filters: only shows pairs where both translations have >= 2-star rating
    and gap < 2, based on the current user's votes.
    Priority: composite score using ELO closeness, RD uncertainty, pair hunger,
    and same-rated bonus.
    """

    username = session.get("username", "Guest")
    user = db_session.query(User).filter(User.username == username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    target_models_str = request.args.get("target_models", "")
    target_models = {m.strip() for m in target_models_str.split(",") if m.strip()}

    t1_alias = aliased(Translation)
    t2_alias = aliased(Translation)
    v1_alias = aliased(Vote)
    v2_alias = aliased(Vote)

    # Base query for all relevant pairs (same query_id, different translations)
    # with vote-based filtering: both >= 2-star and gap < 2, constrained to current user
    base_query = (
        db_session.query(
            t1_alias.id.label("t1_id"),
            t2_alias.id.label("t2_id"),
            t1_alias.model.label("t1_model"),
            t2_alias.model.label("t2_model"),
            t1_alias.query_id,
            v1_alias.rating.label("t1_rating"),
            v2_alias.rating.label("t2_rating"),
        )
        .join(
            t2_alias,
            and_(t1_alias.query_id == t2_alias.query_id, t1_alias.id < t2_alias.id),
        )
        .join(
            v1_alias,
            and_(v1_alias.translation_id == t1_alias.id, v1_alias.user_id == user.id),
        )
        .join(
            v2_alias,
            and_(v2_alias.translation_id == t2_alias.id, v2_alias.user_id == user.id),
        )
        .filter(
            v1_alias.rating >= 2,
            v2_alias.rating >= 2,
            func.abs(v1_alias.rating - v2_alias.rating) < 2,
        )
    )

    if target_models:
        base_query = base_query.filter(or_(t1_alias.model.in_(target_models), t2_alias.model.in_(target_models)))

    # Subquery to find already compared pairs for this user in explicit UI mode
    compared_subq = (
        db_session.query(PairwiseComparison)
        .filter(
            PairwiseComparison.user_id == user.id,
            PairwiseComparison.source == "explicit",
        )
        .subquery()
    )

    # Left join to filter out already compared pairs dynamically
    uncompared_query = base_query.outerjoin(
        compared_subq,
        or_(
            and_(
                t1_alias.id == compared_subq.c.translation_a_id,
                t2_alias.id == compared_subq.c.translation_b_id,
            ),
            and_(
                t1_alias.id == compared_subq.c.translation_b_id,
                t2_alias.id == compared_subq.c.translation_a_id,
            ),
        ),
    ).filter(compared_subq.c.id.is_(None))

    # Fetch ALL uncompared pairs (no random limit(100) batch)
    uncompared_batch = uncompared_query.all()
    if not uncompared_batch:
        return jsonify({"error": "All pairs have been compared"}), 404

    elo_service = get_elo_service()
    all_rankings = {r["model"]: r for r in elo_service.get_all_rankings()}

    # Get pair-level explicit comparison counts for pair hunger
    pair_counts = get_pair_comparison_counts()

    # Build set of active model keys for pair classification
    conf = get_config()
    active_models = {k for k, m in conf.MODELS.items() if m.get("is_active", True)}

    # Classify pairs: both-active, mixed (one active, one disabled), both-disabled
    both_active = []
    mixed = []
    for row in uncompared_batch:
        t1_active = row.t1_model in active_models
        t2_active = row.t2_model in active_models

        ranking_a = all_rankings.get(row.t1_model, {})
        ranking_b = all_rankings.get(row.t2_model, {})
        elo_a = ranking_a.get("elo_rating", 1500.0)
        rd_a = ranking_a.get("rating_deviation", 350.0)
        elo_b = ranking_b.get("elo_rating", 1500.0)
        rd_b = ranking_b.get("rating_deviation", 350.0)

        pair_key = (min(row.t1_model, row.t2_model), max(row.t1_model, row.t2_model))
        pair_count = pair_counts.get(pair_key, 0)

        same_rating = row.t1_rating == row.t2_rating

        priority = _compute_pair_priority(elo_a, rd_a, elo_b, rd_b, pair_count, same_rating)

        if t1_active and t2_active:
            both_active.append((row, priority))
        elif t1_active or t2_active:
            mixed.append((row, priority))
        # Both disabled: skip entirely — no value comparing two discontinued models

    # Two-stage selection: prefer both-active, fall back to mixed
    candidate_pairs = both_active if both_active else mixed
    if not candidate_pairs:
        return jsonify({"error": "No eligible pairs to compare"}), 404

    # Sort by composite priority (descending) -> highest priority first
    candidate_pairs.sort(key=lambda x: x[1], reverse=True)

    # Take top 5 candidates with highest priority and pick one randomly
    top_candidates = candidate_pairs[:5]
    selected_pair_row, _ = random.choice(top_candidates)

    # Optimized: Batch fetch translations to reduce roundtrips
    translations = (
        db_session.query(Translation)
        .filter(Translation.id.in_([selected_pair_row.t1_id, selected_pair_row.t2_id]))
        .all()
    )
    t_map = {t.id: t for t in translations}
    t1 = t_map.get(selected_pair_row.t1_id)
    t2 = t_map.get(selected_pair_row.t2_id)

    query = db_session.get(Query, selected_pair_row.query_id)

    if not t1 or not t2 or not query:
        return jsonify({"error": "Data not found"}), 404

    stats = _get_user_comparison_stats(int(user.id))

    # Shuffle t1 and t2 for display to eliminate position bias
    if random.choice([True, False]):
        t1, t2 = t2, t1

    return jsonify(
        {
            "query_id": query.id,
            "source_text": query.source_text if query else "",
            "translations": [
                {
                    "id": t1.id,
                    "text": t1.translation,
                    "model": t1.model,
                    "base_model": conf.MODELS.get(str(t1.model), {}).get("base_model", t1.model),
                    "preset_name": conf.MODELS.get(str(t1.model), {}).get("preset_name"),
                },
                {
                    "id": t2.id,
                    "text": t2.translation,
                    "model": t2.model,
                    "base_model": conf.MODELS.get(str(t2.model), {}).get("base_model", t2.model),
                    "preset_name": conf.MODELS.get(str(t2.model), {}).get("preset_name"),
                },
            ],
            "stats": stats,
        }
    )


def _get_user_comparison_stats(user_id: int):
    """Helper to calculate user comparison stats efficiently.

    Counts eligible pairs using the same criteria as get_random_comparison:
    both translations must be from active models, have >= 2-star rating
    from this user, and have a rating gap < 2.
    """
    conf = get_config()
    active_model_keys = {k for k, m in conf.MODELS.items() if m.get("is_active", True)}

    # 1. Count user's explicit comparisons (only for active models)
    comparisons_count = (
        db_session.query(func.count(PairwiseComparison.id))
        .filter(
            PairwiseComparison.user_id == user_id,
            PairwiseComparison.source == "explicit",
        )
        .scalar()
    ) or 0

    # 2. Count eligible pairs: same query, both active models, both voted
    #    >= 2-star by this user, with rating gap < 2
    t1_alias = aliased(Translation)
    t2_alias = aliased(Translation)
    v1_alias = aliased(Vote)
    v2_alias = aliased(Vote)

    eligible_pairs_count = (
        db_session.query(func.count())
        .select_from(t1_alias)
        .join(
            t2_alias,
            and_(
                t1_alias.query_id == t2_alias.query_id,
                t1_alias.id < t2_alias.id,
            ),
        )
        .join(
            v1_alias,
            and_(
                v1_alias.translation_id == t1_alias.id,
                v1_alias.user_id == user_id,
            ),
        )
        .join(
            v2_alias,
            and_(
                v2_alias.translation_id == t2_alias.id,
                v2_alias.user_id == user_id,
            ),
        )
        .filter(
            t1_alias.model.in_(active_model_keys),
            t2_alias.model.in_(active_model_keys),
            v1_alias.rating >= 2,
            v2_alias.rating >= 2,
            func.abs(v1_alias.rating - v2_alias.rating) < 2,
        )
        .scalar()
    ) or 0

    pairs_remaining = max(0, eligible_pairs_count - comparisons_count)

    return {
        "comparisons_done": comparisons_count,
        "pairs_remaining": pairs_remaining,
        "total_pairs": eligible_pairs_count,
    }


@main_bp.route("/compare/submit", methods=["POST"])
@login_required
def submit_comparison() -> Response | tuple[Response, int]:
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

    # Get translations - Optimized: Batch fetch to reduce roundtrips
    translations = db_session.query(Translation).filter(Translation.id.in_(translation_ids)).all()
    t_map = {t.id: t for t in translations}
    t1 = t_map.get(translation_ids[0])
    t2 = t_map.get(translation_ids[1])

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
            query_id=int(query_id),
            user_id=int(user.id),
            winner_model=str(winner_model) if winner_model else None,
            loser_model=str(loser_model) if loser_model else None,
            translation_a_id=int(t1.id),
            translation_b_id=int(t2.id),
            source="explicit",
        )
        invalidate_caches()
        return jsonify({"status": "success"})
    except Exception as e:
        current_app.logger.exception("Error recording comparison")
        return jsonify({"error": str(e)}), 500
