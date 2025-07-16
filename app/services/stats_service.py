from app.database import db_session
from app.repositories.translation_repository import TranslationRepository
from app.repositories.vote_repository import VoteRepository


def calculate_model_scores():
    """
    Calculates comprehensive scores and stats for each model, including cost-effectiveness.
    """
    vote_repo = VoteRepository(db_session)
    translation_repo = TranslationRepository(db_session)

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
            }

    # Aggregate total cost and the number of times each model's translation was generated
    for t in translations:
        model_stats[t.model]["appearances"] += 1
        model_stats[t.model]["total_cost"] += t.cost if t.cost else 0.0

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
        # Calculate performance per dollar
        score_per_dollar = (total_score / total_cost) if total_cost > 0 else 0

        stats_list.append(
            {
                "model_name": model_name,
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
            }
        )

    # Sort by average_score in descending order to rank the models
    stats_list.sort(key=lambda x: x["average_score"], reverse=True)

    return stats_list
