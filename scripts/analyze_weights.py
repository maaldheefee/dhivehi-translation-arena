import os
import sys

# Add app to path
sys.path.append(os.getcwd())

from app import create_app
from app.services.stats_service import calculate_model_scores

app = create_app()

with app.app_context():
    stats = calculate_model_scores()

    print(
        f"{'Model':<30} | {'Avg Rating':<10} | {'ELO':<6} | {'Norm Rade':<10} | {'Norm ELO':<10} | {'Comb':<6} | {'Diff':<6}"
    )
    print("-" * 100)

    for s in stats:
        # Re-calculate normalizations to be sure
        avg_score = s["average_score"]
        elo = s["elo_rating"]

        norm_avg = (avg_score + 2) / 5
        norm_avg = max(0.0, min(1.0, norm_avg))

        norm_elo = (elo - 1000) / 1000
        norm_elo = max(0.0, min(1.0, norm_elo))

        diff = norm_avg - norm_elo

        print(
            f"{s['model_name']:<30} | {avg_score:>10.2f} | {elo:>6.0f} | {norm_avg:>10.2f} | {norm_elo:>10.2f} | {s['combined_score']:>6.2f} | {diff:>6.2f}"
        )
