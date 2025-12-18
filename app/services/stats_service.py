import datetime
from collections import defaultdict
from typing import cast

from sqlalchemy.orm import Session

from app.config import get_config
from app.database import db_session
from app.models import ModelELO
from app.repositories.translation_repository import TranslationRepository
from app.repositories.vote_repository import VoteRepository

config = get_config()


def calculate_model_scores():
    """
    Calculates comprehensive scores and stats for each model, including cost-effectiveness.
    Now includes ELO ratings from pairwise comparisons.
    """
    session = cast(Session, db_session)
    vote_repo = VoteRepository(session)
    translation_repo = TranslationRepository(session)

    votes = vote_repo.get_all()
    translations = translation_repo.get_all()

    # Get ELO ratings for all models
    elo_records = {r.model: r for r in session.query(ModelELO).all()}

    model_stats = {}

    # Initialize all models from the translations table to capture costs
    # even for models that haven't received votes yet.
    for t in translations:
        if t.model not in model_stats:
            model_stats[t.model] = {
                "score": 0,
                "total_cost": 0.0,
                "appearances": 0,  # Total times generated
                "votes_cast": 0,
                "excellent_count": 0,
                "good_count": 0,
                "okay_count": 0,
                "rejected_count": 0,
                "source_word_count": 0,
            }

    # Aggregate total cost and the number of times each model's translation was generated
    for t in translations:
        model_stats[t.model]["appearances"] += 1
        model_stats[t.model]["total_cost"] += t.cost if t.cost else 0.0
        if t.query and t.query.source_text:
            model_stats[t.model]["source_word_count"] += len(
                t.query.source_text.split()
            )

    # Aggregate scores based on votes
    for vote in votes:
        model_name = vote.translation.model
        if model_name in model_stats:
            model_stats[model_name]["votes_cast"] += 1

            if vote.rating == 3:
                model_stats[model_name]["score"] += 3
                model_stats[model_name]["excellent_count"] += 1
            elif vote.rating == 2:
                model_stats[model_name]["score"] += 1
                model_stats[model_name]["good_count"] += 1
            elif vote.rating == 1:
                model_stats[model_name]["okay_count"] += 1
            elif vote.rating == -1:
                model_stats[model_name]["score"] -= 2
                model_stats[model_name]["rejected_count"] += 1

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
        elo_wins = (elo_record.wins or 0) if elo_record else 0
        elo_losses = (elo_record.losses or 0) if elo_record else 0
        elo_ties = (elo_record.ties or 0) if elo_record else 0
        elo_total = elo_wins + elo_losses + elo_ties
        elo_win_rate = (elo_wins / elo_total * 100) if elo_total > 0 else 0.0

        # --- Advanced Scoring Logic ---

        # 1. Normalize Average Score: Map [-2, 3] -> [0, 1]
        # Range is 5. -2 maps to 0. 3 maps to 1.
        # norm = (score - min) / (max - min) = (score + 2) / 5
        normalized_avg_score = (average_score + 2) / 5
        normalized_avg_score = max(0.0, min(1.0, normalized_avg_score))  # Clamp

        # 2. Normalize ELO: Map [1000, 2000] -> [0, 1]
        # Center 1500 -> 0.5
        normalized_elo = (elo_rating - 1000) / 1000
        normalized_elo = max(0.0, min(1.0, normalized_elo))  # Clamp

        # 3. Combined Score (40% Rating, 60% ELO - corrects for optimism bias in ratings)
        combined_score = (normalized_avg_score * 0.4) + (normalized_elo * 0.6)

        # 4. Bang for Buck: (Combined Score ^ 3) / Cost per Unit
        # User requested stronger filtering for bad/cheap models.
        # 1. Threshold: If score is below 0.4 (approx 2.0 star rating equivalent mixed with low ELO),
        #    it is considered unusable, so Value = 0.
        # 2. Cubic Power: Cubing the score rewards high quality much more than squaring.

        if projected_cost_100k == 0:
            # For free models or zero cost, treated as very high value.
            # Use a small epsilon for cost ~ $0.01 per 100k words
            projected_cost_100k = 0.01

        raw_bang_for_buck = ((10 * combined_score) ** 4) / projected_cost_100k

        # Get model config
        model_config = config.MODELS.get(model_name, {})

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

    # Normalize Bang for Buck (0-10 scale)
    if stats_list:
        max_bb = max(s["bang_for_buck"] for s in stats_list)
        for s in stats_list:
            if max_bb > 0:
                s["bang_for_buck"] = (s["bang_for_buck"] / max_bb) * 10
            else:
                s["bang_for_buck"] = 0

    stats_list.sort(key=lambda x: x["combined_score"], reverse=True)

    return stats_list


def get_model_usage_stats() -> dict[str, int]:
    """
    Returns a dictionary mapping model names to their usage count (appearances).
    """
    stats = calculate_model_scores()
    return {item["model_name"]: item["appearances"] for item in stats}


def calculate_global_stats():
    """
    Calculates global statistics for the dashboard.
    """
    session = cast(Session, db_session)
    vote_repo = VoteRepository(session)
    translation_repo = TranslationRepository(session)

    translations = translation_repo.get_all()
    votes = vote_repo.get_all()

    total_cost = 0.0
    total_generations = len(translations)
    voted_generations = len({v.translation_id for v in votes})

    # Cost over time (Current Month and Current Day)
    now = datetime.datetime.now()
    current_month_cost = 0.0
    current_day_cost = 0.0

    for t in translations:
        cost = t.cost if t.cost else 0.0
        total_cost += cost

        if (
            t.created_at
            and t.created_at.year == now.year
            and t.created_at.month == now.month
        ):
            current_month_cost += cost
            if t.created_at.day == now.day:
                current_day_cost += cost

    return {
        "total_cost": total_cost,
        "total_generations": total_generations,
        "voted_generations": voted_generations,
        "vote_percentage": (voted_generations / total_generations * 100)
        if total_generations > 0
        else 0,
        "current_month_cost": current_month_cost,
        "current_day_cost": current_day_cost,
    }


def get_monthly_spending_stats():
    """
    Returns monthly spending data for the last 12 months.
    """
    session = cast(Session, db_session)
    translation_repo = TranslationRepository(session)
    translations = translation_repo.get_all()

    monthly_data = defaultdict(float)
    now = datetime.datetime.now()

    # Initialize last 12 months with 0
    for i in range(12):
        d = now - datetime.timedelta(days=i * 30)
        key = d.strftime("%Y-%m")
        monthly_data[key] = 0.0

    for t in translations:
        if t.created_at and t.cost:
            key = t.created_at.strftime("%Y-%m")
            monthly_data[key] += t.cost

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
    translation_repo = TranslationRepository(session)
    vote_repo = VoteRepository(session)

    translations = translation_repo.get_all()
    votes = vote_repo.get_all()

    voted_translation_ids = {v.translation_id for v in votes}

    grouped_stats = {}

    # Pre-calculate a display name mapping: upstream_name -> shortest_display_name
    upstream_display_names = {}
    upstream_base_models = {}
    for conf in config.MODELS.values():
        u_name = conf["name"]
        d_name = conf["display_name"]
        b_name = conf.get("base_model")

        if u_name not in upstream_display_names or len(d_name) < len(
            upstream_display_names[u_name]
        ):
            upstream_display_names[u_name] = d_name
        # If we have a base_model defined, map it to the upstream name
        # We can just take the first one we find, or any, since they should be consistent
        # for the same upstream model usually.
        if b_name and u_name not in upstream_base_models:
            upstream_base_models[u_name] = b_name

    for t in translations:
        model_key = t.model
        # Fallback if model missing from config
        upstream_name = model_key
        display_name = model_key

        if model_key in config.MODELS:
            upstream_name = config.MODELS[model_key]["name"]
            display_name = upstream_display_names.get(upstream_name, upstream_name)

        if upstream_name not in grouped_stats:
            # Determine base_model to show
            # Use the pre-calculated base_model if available, else fallback to display_name
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
        stats["total_cost"] += t.cost if t.cost else 0.0
        stats["total_generations"] += 1
        if t.id in voted_translation_ids:
            stats["voted_generations"] += 1

        if t.query and t.query.source_text:
            stats["source_word_count"] += len(t.query.source_text.split())

    result = []
    for s in grouped_stats.values():
        projected = 0.0
        if s["source_word_count"] > 0:
            projected = (s["total_cost"] / s["source_word_count"]) * 100000

        s["projected_cost_100k"] = projected
        result.append(s)

    result.sort(key=lambda x: x["total_cost"], reverse=True)
    return result
