import json
import os
import sys

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import get_config
from app.models import (
    ModelELO,
    PairwiseComparison,
    Query,
    Translation,
)


def get_db_session():
    config = get_config()
    engine = create_engine(config.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    return Session()


def analyze_elo(session):
    elos = session.query(ModelELO).order_by(ModelELO.elo_rating.desc()).all()
    results = []
    for elo in elos:
        results.append(
            {
                "model": elo.model,
                "elo": elo.elo_rating,
                "wins": elo.wins,
                "losses": elo.losses,
                "ties": elo.ties,
                "win_rate": elo.win_rate,
            }
        )
    return results


def analyze_pairwise_temperature(session):
    # Find base models with both high and low temp variants
    comparisons = session.query(PairwiseComparison).all()

    # We need to categorize models first.
    # Use config-like logic or heuristics.
    # 0.1 is low, 0.85/1.0 is high.

    high_temp_wins = 0
    low_temp_wins = 0
    total_relevant = 0

    for comp in comparisons:
        winner = comp.winner_model
        loser = comp.loser_model

        if not winner or not loser:
            continue

        # Check if one is high and one is low
        w_temp = "low" if "t0.1" in winner or "t0.3" in winner else "high"
        l_temp = "low" if "t0.1" in loser or "t0.3" in loser else "high"

        if w_temp != l_temp:
            total_relevant += 1
            if w_temp == "high":
                high_temp_wins += 1
            else:
                low_temp_wins += 1

    return {
        "total_cross_temp_comparisons": total_relevant,
        "high_temp_wins": high_temp_wins,
        "low_temp_wins": low_temp_wins,
        "high_temp_win_rate": high_temp_wins / total_relevant
        if total_relevant > 0
        else 0,
    }


def analyze_reasoning_impact(session):
    # Models with 'reasoning' or 'low' in name vs others?
    # Or just check performance of Gemini 3 models vs others.

    elos = session.query(ModelELO).all()
    reasoning_models = [
        m for m in elos if "gemini-3" in m.model or "reasoning" in m.model
    ]
    non_reasoning_models = [m for m in elos if m not in reasoning_models]

    avg_elo_reasoning = (
        sum([m.elo_rating for m in reasoning_models]) / len(reasoning_models)
        if reasoning_models
        else 0
    )
    avg_elo_others = (
        sum([m.elo_rating for m in non_reasoning_models]) / len(non_reasoning_models)
        if non_reasoning_models
        else 0
    )

    return {
        "avg_elo_reasoning_models": avg_elo_reasoning,
        "avg_elo_standard_models": avg_elo_others,
        "reasoning_models_count": len(reasoning_models),
        "standard_models_count": len(non_reasoning_models),
    }


def get_qualitative_examples(session):
    # Find a query with many translations
    # Group translations by query_id

    # query IDs with count of translations > 3
    subquery = (
        session.query(Translation.query_id, func.count(Translation.id).label("count"))
        .group_by(Translation.query_id)
        .having(func.count(Translation.id) >= 3)
        .subquery()
    )

    target_query_ids = session.query(subquery.c.query_id).limit(3).all()
    target_query_ids = [t[0] for t in target_query_ids]

    examples = []
    for qid in target_query_ids:
        query = session.query(Query).get(qid)
        translations = session.query(Translation).filter_by(query_id=qid).all()

        t_data = []
        for t in translations:
            t_data.append(
                {
                    "model": t.model,
                    "text": t.translation,
                    "system_prompt": t.system_prompt,
                }
            )

        examples.append(
            {"query_id": qid, "source": query.source_text, "translations": t_data}
        )
    return examples


def run():
    session = get_db_session()

    data = {
        "elo_ranking": analyze_elo(session),
        "temperature_analysis": analyze_pairwise_temperature(session),
        "reasoning_impact": analyze_reasoning_impact(session),
        "examples": get_qualitative_examples(session),
    }

    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
