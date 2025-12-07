import datetime
from typing import cast

from sqlalchemy.orm import Session

from app.config import get_config
from app.database import db_session
from app.repositories.translation_repository import TranslationRepository
from app.repositories.vote_repository import VoteRepository

config = get_config()


def calculate_model_scores():
    """
    Calculates comprehensive scores and stats for each model, including cost-effectiveness.
    """
    session = cast(Session, db_session)
    vote_repo = VoteRepository(session)
    translation_repo = TranslationRepository(session)

    votes = vote_repo.get_all()
    translations = translation_repo.get_all()

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

        # Calculate average score (normalized by number of votes)
        average_score = (total_score / votes_cast) if votes_cast > 0 else 0
        # Calculate performance per dollar (Bang for Buck)
        score_per_dollar = (total_score / total_cost) if total_cost > 0 else 0

        # Calculate projected cost for 100k words
        source_word_count = stats["source_word_count"]
        projected_cost_100k = 0.0
        if source_word_count > 0:
            cost_per_word = total_cost / source_word_count
            projected_cost_100k = cost_per_word * 100_000

        stats_list.append(
            {
                "model_name": model_name,
                "is_active": config.MODELS.get(model_name, {}).get("is_active", False),
                "score": total_score,
                "appearances": stats["appearances"],
                "votes_cast": votes_cast,
                "excellent_count": stats["excellent_count"],
                "good_count": stats["good_count"],
                "okay_count": stats["okay_count"],
                "rejected_count": stats["rejected_count"],
                "average_score": average_score,
                "total_cost": total_cost,
                "score_per_dollar": score_per_dollar,
                "bang_for_buck": score_per_dollar,  # Alias for template if needed
                "projected_cost_100k": projected_cost_100k,
                "source_word_count": source_word_count,
            }
        )

    # Normalize Bang for Buck (0-10 scale)
    if stats_list:
        max_bb = max(s["score_per_dollar"] for s in stats_list)
        for s in stats_list:
             if max_bb > 0:
                 s["bang_for_buck"] = (s["score_per_dollar"] / max_bb) * 10
             else:
                 s["bang_for_buck"] = 0

    stats_list.sort(key=lambda x: x["average_score"], reverse=True)

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

        if t.created_at and t.created_at.year == now.year and t.created_at.month == now.month:
            current_month_cost += cost
            if t.created_at.day == now.day:
                current_day_cost += cost

    return {
        "total_cost": total_cost,
        "total_generations": total_generations,
        "voted_generations": voted_generations,
        "vote_percentage": (voted_generations / total_generations * 100) if total_generations > 0 else 0,
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

    import datetime
    from collections import defaultdict

    monthly_data = defaultdict(float)
    now = datetime.datetime.now()

    # Initialize last 12 months with 0
    for i in range(12):
        d = now - datetime.timedelta(days=i*30)
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
    return {
        "labels": sorted_months,
        "data": [monthly_data[m] for m in sorted_months]
    }


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
    for conf in config.MODELS.values():
        u_name = conf["name"]
        d_name = conf["display_name"]
        if u_name not in upstream_display_names or len(d_name) < len(upstream_display_names[u_name]):
            upstream_display_names[u_name] = d_name

    for t in translations:
        model_key = t.model
        # Fallback if model missing from config
        upstream_name = model_key
        display_name = model_key

        if model_key in config.MODELS:
            upstream_name = config.MODELS[model_key]["name"]
            display_name = upstream_display_names.get(upstream_name, upstream_name)

        if upstream_name not in grouped_stats:
            grouped_stats[upstream_name] = {
                "model_name": display_name,
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
