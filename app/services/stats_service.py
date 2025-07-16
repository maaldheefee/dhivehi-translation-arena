from app.database import db_session
from app.repositories.vote_repository import VoteRepository


def calculate_model_scores():
    """
    Calculates the scores for each model based on votes.
    """
    vote_repo = VoteRepository(db_session)
    votes = vote_repo.get_all()

    model_stats = {}

    for vote in votes:
        model_name = vote.translation.model
        if model_name not in model_stats:
            model_stats[model_name] = {
                "score": 0,
                "appearances": 0,
                "excellent_count": 0,
                "good_count": 0,
                "okay_count": 0,
                "rejected_count": 0,
            }

        model_stats[model_name]["appearances"] += 1

        if vote.rating == 3:
            model_stats[model_name]["score"] += 3
            model_stats[model_name]["excellent_count"] += 1
        elif vote.rating == 2:
            model_stats[model_name]["score"] += 1
            model_stats[model_name]["good_count"] += 1
        elif vote.rating == 1:
            model_stats[model_name]["score"] += 0
            model_stats[model_name]["okay_count"] += 1
        elif vote.rating == -1:
            model_stats[model_name]["score"] -= 2
            model_stats[model_name]["rejected_count"] += 1

    # Convert to list of dictionaries
    stats_list = []
    for model_name, stats in model_stats.items():
        stats_list.append(
            {
                "model_name": model_name,
                "score": stats["score"],
                "appearances": stats["appearances"],
                "excellent_count": stats["excellent_count"],
                "good_count": stats["good_count"],
                "okay_count": stats["okay_count"],
                "rejected_count": stats["rejected_count"],
            }
        )

    return stats_list
