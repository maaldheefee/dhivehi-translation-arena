from flask import Blueprint, render_template, session

from app.services.stats_service import calculate_model_scores

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/stats")
def stats():
    """Renders the statistics page with model performance data."""
    username = session.get("username", "Guest")
    model_scores = calculate_model_scores()

    # Prepare data for the Chart.js graph
    # The list is already sorted by rank from the service
    chart_labels = [score["model_name"] for score in model_scores]
    chart_data = [score["average_score"] for score in model_scores]
    total_votes = sum(score["votes_cast"] for score in model_scores)

    return render_template(
        "stats.html",
        model_scores=model_scores,
        username=username,
        chart_labels=chart_labels,
        chart_data=chart_data,
        total_votes=total_votes,
    )
