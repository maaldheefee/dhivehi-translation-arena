import datetime
import math
import time
from collections import defaultdict
from typing import NotRequired, TypedDict, cast

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.config import get_config
from app.database import db_session
from app.models import ModelELO, Query, Translation, Vote
from app.services.elo_service import effective_rating_deviation


class GroupedStats(TypedDict):
    model_name: str
    base_model: str
    total_cost: float
    total_generations: int
    voted_generations: int
    source_word_count: int
    projected_cost_100k: NotRequired[float]


def calculate_model_scores():
    """
    Calculates comprehensive scores and stats for each model, including cost-effectiveness.
    Now includes ELO ratings from pairwise comparisons.
    """
    session = cast(Session, db_session)

    # Get ELO ratings for all models
    elo_records = {r.model: r for r in session.query(ModelELO).all()}

    model_stats = {}

    # Query 1: Aggregate appearances, cost, and estimated word count
    # Word count estimation in SQLite: len(text) - len(replace(text, ' ', '')) + 1
    word_count_expr = (
        func.length(func.trim(Query.source_text)) - func.length(func.replace(func.trim(Query.source_text), " ", "")) + 1
    )

    trans_stats = (
        session.query(
            Translation.model,
            func.count(Translation.id).label("appearances"),
            func.sum(Translation.cost).label("total_cost"),
            func.sum(case((Query.source_text != "", word_count_expr), else_=0)).label("source_word_count"),
        )
        .outerjoin(Query, Translation.query_id == Query.id)
        .group_by(Translation.model)
        .all()
    )

    for ts in trans_stats:
        model_stats[ts.model] = {
            "score": 0,
            "total_cost": ts.total_cost or 0.0,
            "appearances": ts.appearances or 0,
            "votes_cast": 0,
            "excellent_count": 0,
            "good_count": 0,
            "okay_count": 0,
            "rejected_count": 0,
            "source_word_count": ts.source_word_count or 0,
        }

    # Query 2: Aggregate votes
    vote_stats = (
        session.query(
            Translation.model,
            func.count(Vote.id).label("votes_cast"),
            func.sum(case((Vote.rating == 3, 1), else_=0)).label("excellent_count"),
            func.sum(case((Vote.rating == 2, 1), else_=0)).label("good_count"),
            func.sum(case((Vote.rating == 1, 1), else_=0)).label("okay_count"),
            func.sum(case((Vote.rating == -1, 1), else_=0)).label("rejected_count"),
            func.sum(
                case(
                    (Vote.rating == 3, 3),
                    (Vote.rating == 2, 1),
                    (Vote.rating == -1, -2),
                    else_=0,
                )
            ).label("score"),
        )
        .select_from(Vote)
        .join(Translation, Vote.translation_id == Translation.id)
        .group_by(Translation.model)
        .all()
    )

    for vs in vote_stats:
        if vs.model in model_stats:
            model_stats[vs.model]["votes_cast"] = vs.votes_cast or 0
            model_stats[vs.model]["excellent_count"] = vs.excellent_count or 0
            model_stats[vs.model]["good_count"] = vs.good_count or 0
            model_stats[vs.model]["okay_count"] = vs.okay_count or 0
            model_stats[vs.model]["rejected_count"] = vs.rejected_count or 0
            model_stats[vs.model]["score"] = vs.score or 0
        else:
            model_stats[vs.model] = {
                "score": vs.score or 0,
                "total_cost": 0.0,
                "appearances": 0,
                "votes_cast": vs.votes_cast or 0,
                "excellent_count": vs.excellent_count or 0,
                "good_count": vs.good_count or 0,
                "okay_count": vs.okay_count or 0,
                "rejected_count": vs.rejected_count or 0,
                "source_word_count": 0,
            }

    # Calculate derived metrics and format for the view
    stats_list = []
    for model_name, stats in model_stats.items():
        votes_cast = stats["votes_cast"]
        total_cost = stats["total_cost"]
        total_score = stats["score"]
        appearances = stats["appearances"]

        # Calculate average score (normalized by number of votes)
        average_score = (total_score / votes_cast) if votes_cast > 0 else 0

        # Projected cost for 100k words
        source_word_count = stats["source_word_count"]
        projected_cost_100k = 0.0
        if source_word_count > 0:
            cost_per_word = total_cost / source_word_count
            projected_cost_100k = cost_per_word * 100_000

        # Get ELO data if available
        elo_record = elo_records.get(model_name)
        elo_rating = elo_record.elo_rating if elo_record else 1500.0
        rating_deviation = (
            effective_rating_deviation(elo_record, datetime.datetime.now(datetime.UTC)) if elo_record else 350.0
        )
        elo_wins = elo_record.wins if elo_record else 0
        elo_losses = elo_record.losses if elo_record else 0
        elo_ties = elo_record.ties if elo_record else 0
        elo_total = elo_wins + elo_losses + elo_ties
        elo_win_rate = (elo_wins / elo_total * 100) if elo_total > 0 else 0.0

        # --- Advanced Scoring Logic ---

        # Canonical relative ordering is Glicko-2. Star ratings remain an
        # independent absolute-quality profile rather than a hidden prior.
        conservative_rating = elo_rating - 2 * rating_deviation
        combined_score = max(0.0, min(1.0, (conservative_rating - 1000) / 1000))

        # 4. Bang for Buck: Soft floor + cubic quality / log(cost)
        # Soft floor: subtract 0.3 from combined_score so models below 0.3 get
        # zero, and models just above 0.3 start with very low value.
        # Logarithmic cost denominator compresses the ~200x cost range so
        # quality can compete with cheapness.
        if projected_cost_100k == 0:
            projected_cost_100k = 0.01

        quality = max(0.0, combined_score - 0.3)
        raw_bang_for_buck = 0.0 if quality <= 0 else (quality**3) / math.log(projected_cost_100k + 1)

        # Get model config
        model_config = get_config().MODELS.get(model_name, {})

        stats_list.append(
            {
                "model_name": model_name,
                "display_name": model_config.get("display_name", model_name),
                "base_model": model_config.get("base_model", model_name),
                "preset_name": model_config.get("preset_name"),
                "is_active": model_config.get("is_active", False),
                "score": total_score,
                "appearances": appearances,
                "votes_cast": votes_cast,
                "excellent_count": stats["excellent_count"],
                "good_count": stats["good_count"],
                "okay_count": stats["okay_count"],
                "rejected_count": stats["rejected_count"],
                "average_score": average_score,
                "total_cost": total_cost,
                "score_per_dollar": raw_bang_for_buck,  # Use the new metric here for sorting/display logic
                "bang_for_buck": raw_bang_for_buck,  # Will be normalized below
                "projected_cost_100k": projected_cost_100k,
                "source_word_count": source_word_count,
                # ELO data
                "elo_rating": elo_rating,
                "rating_deviation": rating_deviation,
                "conservative_rating": conservative_rating,
                "is_provisional": rating_deviation > 200,
                "elo_wins": elo_wins,
                "elo_losses": elo_losses,
                "elo_ties": elo_ties,
                "elo_win_rate": elo_win_rate,
                "combined_score": combined_score,
                # Config data for analysis
                "config": {
                    "temperature": model_config.get("temperature"),
                    "thinking_budget": model_config.get("thinking_budget"),
                    "reasoning": model_config.get("reasoning"),
                },
            }
        )

    # Normalize Bang for Buck (0-10 scale) using logarithmic scaling
    # This prevents cheap models from completely dominating (getting 10)
    # while compressing all others into a narrow 0-3 range.
    # Log scaling spreads values more evenly across the full 0-10 range.
    if stats_list:
        # Apply log transform to spread values more evenly
        for s in stats_list:
            bf = cast(float, s["bang_for_buck"])
            s["bang_for_buck"] = math.log(bf + 1) if bf > 0 else 0

        # Now normalize the log-transformed values to 0-10
        max_bb = max(s["bang_for_buck"] for s in stats_list)
        min_bb = min(s["bang_for_buck"] for s in stats_list)
        range_bb = max_bb - min_bb

        for s in stats_list:
            if range_bb > 0:
                # Scale to 0-10 based on min-max of log values
                s["bang_for_buck"] = ((s["bang_for_buck"] - min_bb) / range_bb) * 10
            else:
                s["bang_for_buck"] = 5  # All same value, default to middle

    stats_list.sort(key=lambda x: (x["conservative_rating"], x["elo_rating"]), reverse=True)

    return stats_list


def calculate_base_model_groups():
    """Group model scores by base_model, showing average scores and sub-presets.

    Returns a list of dicts sorted by group average score (descending):
        {
            "base_model": str,
            "avg_score": float,          # mean of individual average_score
            "avg_combined_score": float,  # mean of individual combined_score
            "total_votes": int,
            "total_cost": float,
            "best_preset": str,           # display_name of highest-scoring preset
            "presets": [                  # sorted by average_score descending
                {model_score dict}, ...
            ],
        }
    """
    model_scores = calculate_model_scores()
    groups: dict[str, list] = defaultdict(list)

    for ms in model_scores:
        base = ms.get("base_model") or ms["model_name"]
        groups[base].append(ms)

    result = []
    for base_model, presets in groups.items():
        total_votes = sum(p["votes_cast"] for p in presets)
        total_cost = sum(p["total_cost"] for p in presets)
        star_scored = [p for p in presets if p["votes_cast"] > 0]
        ranked = [p for p in presets if p["elo_wins"] + p["elo_losses"] + p["elo_ties"] > 0]
        avg_score = sum(p["average_score"] for p in star_scored) / len(star_scored) if star_scored else 0.0
        representative = max(ranked, key=lambda x: x["conservative_rating"]) if ranked else None

        result.append(
            {
                "base_model": base_model,
                "avg_score": avg_score,
                "avg_combined_score": representative["combined_score"] if representative else 0.0,
                "conservative_rating": representative["conservative_rating"] if representative else 800.0,
                "total_votes": total_votes,
                "total_comparisons": sum(p["elo_wins"] + p["elo_losses"] + p["elo_ties"] for p in presets),
                "total_cost": total_cost,
                "best_preset": representative["display_name"] if representative else None,
                "best_preset_score": representative["conservative_rating"] if representative else 0.0,
                "presets": sorted(presets, key=lambda x: x["conservative_rating"], reverse=True),
            }
        )

    result.sort(key=lambda x: x["conservative_rating"], reverse=True)
    return result


def invalidate_caches() -> None:
    """Invalidate all TTL caches after data writes (votes, comparisons)."""
    global _usage_stats_cache, _usage_stats_cache_time
    global _pair_counts_cache, _pair_counts_cache_time
    global _query_difficulty_cache, _query_difficulty_cache_time

    _usage_stats_cache = None
    _usage_stats_cache_time = 0
    _pair_counts_cache = None
    _pair_counts_cache_time = 0
    _query_difficulty_cache = None
    _query_difficulty_cache_time = 0


# Cache for model usage stats to avoid expensive grouping queries on every dashboard load
_usage_stats_cache: dict[str, int] | None = None
_usage_stats_cache_time: float = 0
USAGE_STATS_CACHE_TTL = 300  # 5 minutes


def get_model_usage_stats() -> dict[str, int]:
    """
    Returns a dictionary mapping model names to their usage count (appearances).
    Uses a simple TTL cache to improve performance.
    """
    global _usage_stats_cache, _usage_stats_cache_time

    now = time.time()
    if _usage_stats_cache is not None and (now - _usage_stats_cache_time) < USAGE_STATS_CACHE_TTL:
        return _usage_stats_cache

    session = cast(Session, db_session)

    results = (
        session.query(
            Translation.model,
            func.count(func.distinct(Vote.translation_id)).label("cnt"),
        )
        .join(Vote, Vote.translation_id == Translation.id)
        .group_by(Translation.model)
        .all()
    )

    _usage_stats_cache = {row.model: row.cnt for row in results}
    _usage_stats_cache_time = now

    return _usage_stats_cache


_pair_counts_cache: dict[tuple[str, str], int] | None = None
_pair_counts_cache_time: float = 0
PAIR_COUNTS_CACHE_TTL = 300  # 5 minutes


def get_pair_comparison_counts() -> dict[tuple[str, str], int]:
    """Count explicit comparisons per model pair.

    Uses translation model name joins (not winner/loser columns which are
    NULL for ties). Counts explicit comparisons only — derived comparisons
    are abundant and would swamp pair hunger.

    Returns a dict mapping (model_a, model_b) sorted alphabetically to count.
    Uses a TTL cache to avoid expensive grouping queries.
    """
    global _pair_counts_cache, _pair_counts_cache_time

    now = time.time()
    if _pair_counts_cache is not None and (now - _pair_counts_cache_time) < PAIR_COUNTS_CACHE_TTL:
        return _pair_counts_cache

    from sqlalchemy import case
    from sqlalchemy import func as sql_func
    from sqlalchemy.orm import aliased

    from app.models import PairwiseComparison, Translation

    session = cast(Session, db_session)

    t_a = aliased(Translation)
    t_b = aliased(Translation)

    # Use case expressions for least/greatest to stay PostgreSQL-compatible
    # (func.min/max are aggregates that take a single column, not two args)
    m1_expr = case(
        (t_a.model <= t_b.model, t_a.model),
        else_=t_b.model,
    ).label("m1")
    m2_expr = case(
        (t_a.model <= t_b.model, t_b.model),
        else_=t_a.model,
    ).label("m2")

    results = (
        session.query(
            m1_expr,
            m2_expr,
            sql_func.count().label("cnt"),
        )
        .select_from(PairwiseComparison)
        .join(t_a, t_a.id == PairwiseComparison.translation_a_id)
        .join(t_b, t_b.id == PairwiseComparison.translation_b_id)
        .filter(
            PairwiseComparison.source == "explicit",
            PairwiseComparison.translation_a_id.isnot(None),
            PairwiseComparison.translation_b_id.isnot(None),
        )
        .group_by(m1_expr, m2_expr)
        .all()
    )

    _pair_counts_cache = {}
    for row in results:
        key = (row.m1, row.m2)
        _pair_counts_cache[key] = row.cnt

    _pair_counts_cache_time = now
    return _pair_counts_cache


_query_difficulty_cache: dict[int, str] | None = None
_query_difficulty_cache_time: float = 0
QUERY_DIFFICULTY_CACHE_TTL = 300  # 5 minutes


def get_query_difficulty() -> dict[int, str]:
    """Classify queries by difficulty using model-adjusted residuals.

    residual = actual_rating - model_global_avg_rating
    query_difficulty = -mean(residuals for all votes on this query)

    Tiers:
    - easy: avg residual >= +0.3 (models consistently beat their baseline)
    - hard: avg residual <= -0.3 (models consistently underperform)
    - medium: in between
    - unknown: < 3 votes or < 2 different models

    Returns a dict mapping query_id to difficulty tier string.
    Uses a TTL cache.
    """
    global _query_difficulty_cache, _query_difficulty_cache_time

    now = time.time()
    if _query_difficulty_cache is not None and (now - _query_difficulty_cache_time) < QUERY_DIFFICULTY_CACHE_TTL:
        return _query_difficulty_cache

    from app.config import Config
    from app.models import Query as QueryModel

    session = cast(Session, db_session)

    # Step 1: Compute global average rating per model
    model_avg_ratings = (
        session.query(
            Translation.model,
            func.avg(Vote.rating).label("avg_rating"),
        )
        .join(Vote, Vote.translation_id == Translation.id)
        .group_by(Translation.model)
        .all()
    )
    model_avg_map = {row.model: float(row.avg_rating) for row in model_avg_ratings}

    # Step 2: Compute residuals per vote and aggregate per query
    vote_data = (
        session.query(
            Vote.query_id,
            Translation.model,
            Vote.rating,
        )
        .join(Translation, Vote.translation_id == Translation.id)
        .filter(Vote.rating.isnot(None))
        .all()
    )

    # Group residuals by query_id
    query_residuals: dict[int, list[float]] = defaultdict(list)
    query_models: dict[int, set[str]] = defaultdict(set)
    for v in vote_data:
        model_avg = model_avg_map.get(v.model, 0.0)
        residual = float(v.rating) - model_avg
        query_residuals[int(v.query_id)].append(residual)
        query_models[int(v.query_id)].add(v.model)

    # Step 3: Classify each query
    difficulty_map: dict[int, str] = {}
    for query_id, residuals in query_residuals.items():
        if len(residuals) < Config.DIFFICULTY_MIN_VOTES or len(query_models[query_id]) < Config.DIFFICULTY_MIN_MODELS:
            difficulty_map[query_id] = "unknown"
            continue

        avg_residual = sum(residuals) / len(residuals)
        # Positive residual means models beat their baseline -> easy query
        # Negative residual means models underperformed -> hard query

        if avg_residual >= Config.DIFFICULTY_EASY_THRESHOLD:
            difficulty_map[query_id] = "easy"
        elif avg_residual <= Config.DIFFICULTY_HARD_THRESHOLD:
            difficulty_map[query_id] = "hard"
        else:
            difficulty_map[query_id] = "medium"

    # Any queries with no votes at all are unknown
    all_query_ids = {int(q.id) for q in session.query(QueryModel).all()}
    for qid in all_query_ids:
        if qid not in difficulty_map:
            difficulty_map[qid] = "unknown"

    _query_difficulty_cache = difficulty_map
    _query_difficulty_cache_time = now
    return _query_difficulty_cache


def calculate_global_stats():
    """
    Calculates global statistics for the dashboard.
    """
    session = cast(Session, db_session)

    total_generations = session.query(func.count(Translation.id)).scalar() or 0
    voted_generations = session.query(func.count(func.distinct(Vote.translation_id))).scalar() or 0
    total_cost = session.query(func.sum(Translation.cost)).scalar() or 0.0

    now = datetime.datetime.now(datetime.UTC)
    start_of_month = datetime.datetime(now.year, now.month, 1, tzinfo=datetime.UTC)
    start_of_day = datetime.datetime(now.year, now.month, now.day, tzinfo=datetime.UTC)

    current_month_cost = (
        session.query(func.sum(Translation.cost)).filter(Translation.created_at >= start_of_month).scalar() or 0.0
    )

    current_day_cost = (
        session.query(func.sum(Translation.cost)).filter(Translation.created_at >= start_of_day).scalar() or 0.0
    )

    return {
        "total_cost": total_cost,
        "total_generations": total_generations,
        "voted_generations": voted_generations,
        "vote_percentage": (voted_generations / total_generations * 100) if total_generations > 0 else 0,
        "current_month_cost": current_month_cost,
        "current_day_cost": current_day_cost,
    }


def get_monthly_spending_stats() -> dict[str, list[float] | list[str]]:
    """
    Returns monthly spending data for the last 12 months.
    """
    session = cast(Session, db_session)

    monthly_data = defaultdict(float)
    now = datetime.datetime.now(datetime.UTC)

    # Initialize last 12 months with 0
    for i in range(12):
        d = now - datetime.timedelta(days=i * 30)
        key = d.strftime("%Y-%m")
        monthly_data[key] = 0.0

    # Calculate 12 months ago to filter the query and make it faster
    twelve_months_ago = now - datetime.timedelta(days=365)

    month_str = func.strftime("%Y-%m", Translation.created_at)
    monthly_costs = (
        session.query(month_str.label("month"), func.sum(Translation.cost).label("total"))
        .filter(Translation.cost.isnot(None), Translation.created_at >= twelve_months_ago)
        .group_by(month_str)
        .all()
    )

    for row in monthly_costs:
        if row.month and row.month in monthly_data:
            monthly_data[row.month] += row.total or 0.0

    # Sort by date
    sorted_months = sorted(monthly_data.keys())

    # Filter to only keep relevant range (last 12 months roughly) or just all available
    # For chart.js we return two lists: labels and data
    return {"labels": sorted_months, "data": [monthly_data[m] for m in sorted_months]}


def get_cost_breakdown():
    """
    Returns cost statistics grouped by upstream model ID (combining configurations).
    """
    session = cast(Session, db_session)

    # Pre-calculate a display name mapping: upstream_name -> shortest_display_name
    upstream_display_names = {}
    upstream_base_models = {}
    for conf in get_config().MODELS.values():
        u_name = conf["name"]
        d_name = conf["display_name"]
        b_name = conf.get("base_model")

        if u_name not in upstream_display_names or len(d_name) < len(upstream_display_names[u_name]):
            upstream_display_names[u_name] = d_name
        if b_name and u_name not in upstream_base_models:
            upstream_base_models[u_name] = b_name

    # Word count estimation in SQLite
    word_count_expr = (
        func.length(func.trim(Query.source_text)) - func.length(func.replace(func.trim(Query.source_text), " ", "")) + 1
    )

    trans_stats = (
        session.query(
            Translation.model,
            func.count(Translation.id).label("total_generations"),
            func.sum(Translation.cost).label("total_cost"),
            func.sum(case((Query.source_text != "", word_count_expr), else_=0)).label("source_word_count"),
        )
        .outerjoin(Query, Translation.query_id == Query.id)
        .group_by(Translation.model)
        .all()
    )

    # For voted_generations, we need count of DISTINCT translations that received a vote per model
    voted_stats = (
        session.query(
            Translation.model,
            func.count(func.distinct(Vote.translation_id)).label("voted_generations"),
        )
        .select_from(Vote)
        .join(Translation, Vote.translation_id == Translation.id)
        .group_by(Translation.model)
        .all()
    )

    voted_map = {row.model: row.voted_generations for row in voted_stats}

    grouped_stats: dict[str, GroupedStats] = {}

    for row in trans_stats:
        model_key = str(row.model)
        # Fallback if model missing from config
        upstream_name = model_key
        display_name = model_key

        cfg = get_config()
        if model_key in cfg.MODELS:
            upstream_name = cfg.MODELS[model_key]["name"]
            display_name = upstream_display_names.get(upstream_name, upstream_name)

        if upstream_name not in grouped_stats:
            # Determine base_model to show
            base_model_name = upstream_base_models.get(upstream_name, display_name)

            grouped_stats[upstream_name] = {
                "model_name": display_name,
                "base_model": base_model_name,
                "total_cost": 0.0,
                "total_generations": 0,
                "voted_generations": 0,
                "source_word_count": 0,
            }

        stats = grouped_stats[upstream_name]
        stats["total_cost"] += row.total_cost or 0.0
        stats["total_generations"] += row.total_generations or 0
        stats["voted_generations"] += voted_map.get(model_key, 0)
        stats["source_word_count"] += row.source_word_count or 0

    result = []
    for s in grouped_stats.values():
        projected = 0.0
        if s["source_word_count"] > 0:
            projected = (s["total_cost"] / s["source_word_count"]) * 100000

        s["projected_cost_100k"] = projected
        result.append(s)

    result.sort(key=lambda x: x["total_cost"], reverse=True)
    return result
