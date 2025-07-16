from flask import Blueprint, render_template, session

from app.services.stats_service import calculate_model_scores

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/stats")
def stats():
    """Renders the statistics page."""
    username = session.get("username", "Guest")
    model_scores = calculate_model_scores()
    return render_template("stats.html", model_scores=model_scores, username=username)
