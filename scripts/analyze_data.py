"""Export structured data from the Dhivehi Translation Arena for report generation.

Outputs a single JSON blob containing:
- Leaderboard data (same schema as the stats page "Copy Analysis Prompt" button)
- Temperature analysis (using model config from models.yaml, not string matching)
- Reasoning analysis (using model config from models.yaml, not string matching)
- Qualitative examples (source text + translations + vote ratings, selected for diversity)

Usage:
    uv run python scripts/analyze_data.py
    uv run python scripts/analyze_data.py --prompt  # wraps in the analysis prompt template
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file (same as the Flask app does in development)
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from datetime import UTC

from app.config import get_config
from app.database import db_session
from app.models import (
    PairwiseComparison,
    Query,
    Translation,
    Vote,
)
from app.services.stats_service import calculate_global_stats, calculate_model_scores

METHODOLOGY_TEXT = (
    "The results are from an LLM arena where Large Language Models (LLMs) are "
    "scored and voted on for the quality and correctness of English/Arabic to "
    "Dhivehi translations. Users vote on a scale of 1 to 3 stars (or -1 for "
    "rejection). These scores are averaged to produce a preliminary rating. To "
    "refine the ranking, translations are also combined into pairs for Glicko-2 "
    "comparison, allowing for relative evaluation even when ratings are "
    "identical. A final score, normalized to a 0-1 range, is calculated as a "
    "convex blend of the normalized Glicko-2 rating and the normalized average "
    "star rating, weighted by a confidence factor derived from the Glicko-2 "
    "rating deviation (RD). When RD is low (high confidence), the Glicko-2 "
    "rating dominates; when RD is high (low confidence, e.g. new or "
    "under-tested models), star ratings dominate. Note that models use a "
    "default temperature of 0.85, while thinking/reasoning models use their "
    "specific default settings unless configured otherwise."
)

RATING_LABELS = {3: "excellent", 2: "good", 1: "okay", -1: "rejected"}


def get_db_session() -> Session:
    """Create a DB session and configure the app's scoped session.

    The stats_service functions use db_session directly, so we need to
    configure it with an engine before calling them.
    """
    config = get_config()
    engine = create_engine(config.DATABASE_URI)
    session_factory = sessionmaker(bind=engine)
    # Configure the app's scoped session so stats_service can use it
    db_session.configure(bind=engine)
    return session_factory()


def detect_source_language(text: str) -> str:
    """Heuristically detect Arabic vs English source text."""
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
    return "arabic" if arabic_chars > len(text) * 0.15 else "english"


def build_leaderboard_data() -> dict[str, Any]:
    """Build the same JSON structure as the stats page copy-prompt button."""
    model_scores = calculate_model_scores()
    global_stats = calculate_global_stats()
    total_votes = sum(s["votes_cast"] for s in model_scores)

    return {
        "metadata": {
            "generated_at": _now_iso(),
            "total_votes": total_votes,
            "total_translations": global_stats["total_generations"],
            "methodology": METHODOLOGY_TEXT,
        },
        "models": [
            {
                "name": s["display_name"],
                "base_model": s["base_model"],
                "preset": s["preset_name"],
                "avg_score": s["average_score"],
                "elo": s["elo_rating"],
                "rating_deviation": s["rating_deviation"],
                "combined_score": s["combined_score"],
                "elo_details": {
                    "wins": s["elo_wins"],
                    "losses": s["elo_losses"],
                    "ties": s["elo_ties"],
                },
                "win_rate": s["elo_win_rate"],
                "votes": s["votes_cast"],
                "vote_distribution": {
                    "excellent": s["excellent_count"],
                    "good": s["good_count"],
                    "okay": s["okay_count"],
                    "rejected": s["rejected_count"],
                },
                "cost_per_100k": s["projected_cost_100k"],
                "bang_for_buck": s["bang_for_buck"],
                "is_active": s["is_active"],
                "config": s["config"],
            }
            for s in model_scores
        ],
    }


def analyze_temperature(session: Session) -> dict[str, Any]:
    """Analyze temperature effects using model config from models.yaml.

    Only counts comparisons within the same base model to isolate the
    temperature variable. Uses explicit comparisons only to avoid
    circularity with derived comparisons (which are manufactured from
    star ratings that already encode temperature effects).
    """
    config = get_config()
    models = config.MODELS

    # Build model -> (base_model, temp_category) mapping from config
    model_info: dict[str, tuple[str | None, str]] = {}
    for key, cfg in models.items():
        temp = cfg.get("temperature")
        base = cfg.get("base_model")
        if temp is None:
            category = "unknown"
        elif temp <= 0.35:
            category = "low"
        else:
            category = "high"
        model_info[key] = (base, category)

    # Count explicit comparisons only, within same base model
    comparisons = (
        session.query(PairwiseComparison)
        .filter(PairwiseComparison.source == "explicit")
        .filter(PairwiseComparison.winner_model.isnot(None))
        .filter(PairwiseComparison.loser_model.isnot(None))
        .all()
    )

    high_wins = 0
    low_wins = 0
    ties = 0
    total = 0

    # Track per-base-model breakdown
    per_base: dict[str, dict[str, int]] = defaultdict(lambda: {"high_wins": 0, "low_wins": 0, "ties": 0, "total": 0})

    for comp in comparisons:
        winner = comp.winner_model
        loser = comp.loser_model
        if winner not in model_info or loser not in model_info:
            continue

        w_base, w_cat = model_info[winner]
        l_base, l_cat = model_info[loser]

        # Only compare within same base model
        if w_base is None or w_base != l_base:
            continue
        if w_cat == "unknown" or l_cat == "unknown":
            continue
        if w_cat == l_cat:
            continue  # Same temperature category, not useful

        total += 1
        base_key = w_base
        per_base[base_key]["total"] += 1

        # Check for tie (score == 0.5 or winner/loser both null)
        if comp.score is not None and abs(comp.score - 0.5) < 0.01:
            ties += 1
            per_base[base_key]["ties"] += 1
        elif w_cat == "high":
            high_wins += 1
            per_base[base_key]["high_wins"] += 1
        else:
            low_wins += 1
            per_base[base_key]["low_wins"] += 1

    return {
        "total_cross_temp_comparisons": total,
        "high_temp_wins": high_wins,
        "low_temp_wins": low_wins,
        "ties": ties,
        "high_temp_win_rate": high_wins / total if total > 0 else 0,
        "low_temp_win_rate": low_wins / total if total > 0 else 0,
        "per_base_model": {
            base: {
                "high_wins": d["high_wins"],
                "low_wins": d["low_wins"],
                "ties": d["ties"],
                "total": d["total"],
                "high_win_rate": d["high_wins"] / d["total"] if d["total"] > 0 else 0,
                "low_win_rate": d["low_wins"] / d["total"] if d["total"] > 0 else 0,
            }
            for base, d in sorted(per_base.items())
            if d["total"] > 0
        },
    }


def analyze_reasoning(session: Session) -> dict[str, Any]:
    """Analyze reasoning/thinking impact using model config from models.yaml.

    Groups models by whether they have a `reasoning` config block, and
    compares within the same base model to isolate the reasoning variable.
    """
    config = get_config()
    models = config.MODELS

    # Build model -> (base_model, has_reasoning) mapping
    model_info: dict[str, tuple[str | None, bool]] = {}
    for key, cfg in models.items():
        base = cfg.get("base_model")
        has_reasoning = cfg.get("reasoning") is not None
        model_info[key] = (base, has_reasoning)

    # Get ELO data for all models
    from app.models import ModelELO

    elos = {e.model: e for e in session.query(ModelELO).all()}

    # Group by base model: reasoning vs non-reasoning variants
    base_groups: dict[str, dict[bool, list[str]]] = defaultdict(lambda: {True: [], False: []})
    for model_key, (base, has_reason) in model_info.items():
        if base is None:
            continue
        base_groups[base][has_reason].append(model_key)

    # For each base model with both reasoning and non-reasoning variants,
    # compare average ELO and avg_score
    comparisons = []
    for base, groups in sorted(base_groups.items()):
        if not groups[True] or not groups[False]:
            continue  # No comparison possible

        for r_model in groups[True]:
            for nr_model in groups[False]:
                r_elo = elos.get(r_model)
                nr_elo = elos.get(nr_model)
                if not r_elo or not nr_elo:
                    continue
                comparisons.append(
                    {
                        "base_model": base,
                        "reasoning_model": r_model,
                        "non_reasoning_model": nr_model,
                        "reasoning_elo": r_elo.elo_rating,
                        "non_reasoning_elo": nr_elo.elo_rating,
                        "elo_diff": r_elo.elo_rating - nr_elo.elo_rating,
                        "reasoning_wins": r_elo.wins,
                        "reasoning_losses": r_elo.losses,
                        "reasoning_ties": r_elo.ties,
                        "non_reasoning_wins": nr_elo.wins,
                        "non_reasoning_losses": nr_elo.losses,
                        "non_reasoning_ties": nr_elo.ties,
                    }
                )

    # Overall averages
    all_reasoning = [elos[m] for m, (base, has_r) in model_info.items() if has_r and base is not None and m in elos]
    all_non_reasoning = [
        elos[m] for m, (base, has_r) in model_info.items() if not has_r and base is not None and m in elos
    ]

    return {
        "reasoning_model_count": len(all_reasoning),
        "non_reasoning_model_count": len(all_non_reasoning),
        "avg_elo_reasoning": (sum(e.elo_rating for e in all_reasoning) / len(all_reasoning) if all_reasoning else 0),
        "avg_elo_non_reasoning": (
            sum(e.elo_rating for e in all_non_reasoning) / len(all_non_reasoning) if all_non_reasoning else 0
        ),
        "same_base_comparisons": comparisons,
    }


def get_qualitative_examples(session: Session, n_examples: int = 8) -> list[dict[str, Any]]:
    """Select qualitative examples with maximum rating divergence.

    Picks queries where models received the most different ratings (e.g.,
    one model got Excellent while another got Rejected), as these best
    illustrate model differences. Includes vote data for each translation.

    Selection strategy:
    1. Find queries with >= 2 voted translations from different models
    2. Score each query by rating divergence (max_rating - min_rating)
    3. Pick top N by divergence, with at least 2 Arabic and 2 English sources
    4. Include vote ratings alongside each translation
    """
    # Find queries with multiple voted translations from different models
    query_data = (
        session.query(
            Translation.query_id,
            Translation.id,
            Translation.model,
            Translation.translation,
            Vote.rating,
        )
        .join(Vote, Vote.translation_id == Translation.id)
        .filter(Vote.rating.isnot(None))
        .all()
    )

    # Group by query_id
    queries: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in query_data:
        queries[row.query_id].append(
            {
                "translation_id": row.id,
                "model": row.model,
                "text": row.translation,
                "rating": row.rating,
                "rating_label": RATING_LABELS.get(row.rating, "unknown"),
            }
        )

    # Score each query by rating divergence and number of distinct models
    scored_queries = []
    for qid, translations in queries.items():
        models_set = {t["model"] for t in translations}
        if len(models_set) < 2:
            continue

        ratings = [t["rating"] for t in translations]
        max_rating = max(ratings)
        min_rating = min(ratings)
        divergence = max_rating - min_rating

        query = session.get(Query, qid)
        if not query:
            continue

        source_lang = detect_source_language(query.source_text)

        scored_queries.append(
            {
                "query_id": qid,
                "source": query.source_text,
                "source_language": source_lang,
                "divergence": divergence,
                "max_rating": max_rating,
                "min_rating": min_rating,
                "num_translations": len(translations),
                "num_models": len(models_set),
                "translations": translations,
            }
        )

    # Sort by divergence (desc), then by num_models (desc)
    scored_queries.sort(key=lambda x: (x["divergence"], x["num_models"]), reverse=True)

    # Select with language diversity: at least 2 Arabic, 2 English
    selected: list[dict[str, Any]] = []
    arabic_count = 0
    english_count = 0
    min_per_lang = 2

    # First pass: pick highest divergence, respecting language quotas
    for q in scored_queries:
        if len(selected) >= n_examples:
            break

        lang = q["source_language"]
        if lang == "arabic" and arabic_count < min_per_lang:
            selected.append(q)
            arabic_count += 1
        elif lang == "english" and english_count < min_per_lang:
            selected.append(q)
            english_count += 1
        elif arabic_count >= min_per_lang and english_count >= min_per_lang:
            selected.append(q)
            if lang == "arabic":
                arabic_count += 1
            else:
                english_count += 1

    # Second pass: if we still need more, fill from remaining
    selected_ids = {q["query_id"] for q in selected}
    for q in scored_queries:
        if len(selected) >= n_examples:
            break
        if q["query_id"] not in selected_ids:
            selected.append(q)
            selected_ids.add(q["query_id"])

    # Clean up for output
    result = []
    for q in selected:
        result.append(
            {
                "query_id": q["query_id"],
                "source": q["source"],
                "source_language": q["source_language"],
                "rating_divergence": q["divergence"],
                "translations": q["translations"],
            }
        )

    return result


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def build_analysis_prompt(data: dict[str, Any]) -> str:
    """Wrap the data in the same analysis prompt template as the stats page."""
    return f"""# Dhivehi Translation Arena - Leaderboard Analysis Request

Also include analysis of each family and how it improved or regressed over time.
For example, gemini pro, gemini flash, gemini flash lite, claude opus, claude sonnet, etc.

## Task
Analyze the following leaderboard data from the Dhivehi Translation Arena and provide comprehensive insights into LLM performance for Arabic/English to Dhivehi translation.

## Methodology
{METHODOLOGY_TEXT}

## Dataset Overview
- **Total Votes Cast**: {data["metadata"]["total_votes"]}
- **Total Translations Generated**: {data["metadata"]["total_translations"]}
- **Data Generated**: {data["metadata"]["generated_at"]}

## Analysis Requirements

### 1. Overall Performance Ranking
- Identify the top 5 models based on combined score
- Highlight any models that significantly outperform or underperform expectations
- Note any surprising results or anomalies

### 2. Cost-Effectiveness Analysis
- Identify the best "Bang for Buck" models (high quality at reasonable cost)
- Compare premium vs budget options
- Recommend optimal models for different use cases (quality-first vs cost-first)

### 3. Configuration Impact Analysis
Examine how different configurations affect performance:

**Temperature Effects:**
- Compare low temperature (0.1) vs standard (0.85) variants
- Does low temperature improve consistency? Does it reduce creativity?
- Which model families benefit most from low temperature?

**Reasoning/Thinking Models:**
- Do "thinking" or "reasoning" models justify their higher cost?
- Compare thinking variants to their standard counterparts
- Analyze win/loss ratios for reasoning models

**Model Family Patterns:**
- Compare Anthropic Claude vs Google Gemini families
- Identify family-specific strengths or weaknesses
- Note any consistent patterns across model families

### 4. Vote Distribution Insights
- Analyze the vote distribution (excellent/good/okay/rejected) for each model
- Identify models with polarizing results (high excellent + high rejected)
- Find consensus models (consistent good/excellent ratings)

### 5. ELO vs Rating Discrepancies
- Identify models where ELO rating significantly differs from average star rating
- Explain potential reasons for these discrepancies
- Which metric is more reliable for this use case?

### 6. Recommendations
Based on your analysis, provide:
- Top 3 models for production use
- Best budget option
- Most cost-effective premium option
- Models to avoid and why

## Leaderboard Data (JSON)
```json
{json.dumps(data, indent=2, ensure_ascii=False)}
```

## Qualitative Examples
The following are real translation examples selected for maximum rating divergence
(where models received very different ratings for the same source text).

```json
{json.dumps(data.get("qualitative_examples", []), indent=2, ensure_ascii=False)}
```

Please provide a detailed, data-driven analysis addressing all points above.
Use the qualitative examples to illustrate specific model strengths and weaknesses."""


def run() -> None:
    session = get_db_session()

    # Build leaderboard data (same as stats page)
    data = build_leaderboard_data()

    # Add temperature analysis
    data["temperature_analysis"] = analyze_temperature(session)

    # Add reasoning analysis
    data["reasoning_analysis"] = analyze_reasoning(session)

    # Add qualitative examples
    data["qualitative_examples"] = get_qualitative_examples(session, n_examples=8)

    # Check for --prompt flag
    if "--prompt" in sys.argv:
        print(build_analysis_prompt(data))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
