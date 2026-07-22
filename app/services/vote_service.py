"""Vote service for processing hybrid voting system votes."""

import logging
from itertools import combinations
from typing import cast

from sqlalchemy.orm import Session

from app.database import db_session
from app.models import PairwiseComparison, Translation, Vote
from app.repositories.vote_repository import VoteRepository
from app.services.elo_service import get_elo_service

logger = logging.getLogger(__name__)


def _gap_to_score(gap: int) -> float:
    """Map star rating gap to a fractional Glicko-2 score.

    Rating scale: 3, 2, 1, -1 (NOT 3, 2, 1, 0)
    gap=4 -> 1.0  (3 vs -1, decisive)
    gap=3 -> 0.95 (2 vs -1, strong)
    gap=2 -> 0.85 (3 vs 1, or 1 vs -1, clear)
    gap=1 -> 0.70 (3 vs 2, or 2 vs 1, marginal)
    """
    if gap >= 4:
        return 1.0
    elif gap >= 3:
        return 0.95
    elif gap >= 2:
        return 0.85
    else:
        return 0.70


def _should_skip_pair(r1: int, r2: int) -> bool:
    """Determine if a pair of ratings should be skipped (no comparison recorded).

    Skip rules:
    - Both 3-star: perfection on a trivial query, not comparative skill
    - Both -1-star: both trash, no meaningful comparison
    """
    if r1 == 3 and r2 == 3:
        return True
    if r1 == -1 and r2 == -1:
        return True
    return False


def process_votes(user_id: int, query_id: int, votes_data) -> dict[str, bool | str]:
    """
    Process votes for a query from a user.

    Args:
        user_id (int): The ID of the user casting votes
        query_id (int): The ID of the query being voted on
        votes_data (list): List of vote dictionaries with keys:
            - translation_id (int): ID of the translation being voted on
            - rating (int): Rating value (3=Excellent, 2=Meaning Correct, 1=Understandable, -1=Trash)

    Returns:
        dict: Result of the voting process
    """
    session = cast(Session, db_session)
    vote_repo = VoteRepository(session)

    try:
        # Pre-fetch existing votes for the user and query to avoid N+1 query
        existing_votes = vote_repo.get_by_user_and_query(user_id, query_id)
        vote_map = {v.translation_id: v for v in existing_votes}

        # Process votes with Upsert logic
        processed_votes = []
        for vote_data in votes_data:
            translation_id = vote_data.get("translation_id")
            rating = vote_data.get("rating")

            # Validate data
            if not translation_id:
                continue

            # Validate rating value
            if rating not in [3, 2, 1, -1]:
                continue

            # Check if vote already exists in the pre-fetched map
            existing_vote = vote_map.get(translation_id)

            if existing_vote:
                existing_vote.rating = rating
                vote_repo.update(existing_vote)
                processed_votes.append(
                    {"translation_id": translation_id, "rating": rating}
                )
            else:
                vote = Vote(
                    user_id=user_id,
                    query_id=query_id,
                    translation_id=translation_id,
                    rating=rating,
                )
                vote_repo.add(vote)
                # Update map to avoid creating duplicates if translation_id repeats in votes_data
                vote_map[translation_id] = vote
                processed_votes.append(
                    {"translation_id": translation_id, "rating": rating}
                )

        # Derive pairwise comparisons from ALL persisted votes for this user+query
        all_votes = vote_repo.get_by_user_and_query(user_id, query_id)
        if len(all_votes) >= 2:
            all_votes_data = [
                {"translation_id": v.translation_id, "rating": v.rating}
                for v in all_votes
                if v.rating is not None
            ]
            if len(all_votes_data) >= 2:
                _derive_pairwise_from_votes(session, user_id, query_id, all_votes_data)

    except Exception:
        logger.exception("Error processing votes")
        return {"success": False, "error": "An error occurred while processing votes"}

    else:
        return {"success": True, "message": "Votes processed successfully"}


def _derive_pairwise_from_votes(
    session: Session, user_id: int, query_id: int, votes_data
) -> None:
    """Derive pairwise comparisons from star rating votes.

    Deletes existing derived comparisons for (user_id, query_id) first,
    then re-derives from the complete persisted vote set. Uses fractional
    scoring based on star rating gap and applies tie-skip logic.

    After re-derivation, rebuilds all Glicko-2 ratings from stored
    comparisons to ensure live ModelELO matches the source of truth.
    """
    elo_service = get_elo_service(session)

    # Delete existing derived comparisons for this user+query (mutable derived comparisons)
    session.query(PairwiseComparison).filter(
        PairwiseComparison.user_id == user_id,
        PairwiseComparison.query_id == query_id,
        PairwiseComparison.source == "derived",
    ).delete()
    session.flush()

    # Pre-fetch translations to avoid N+1 query
    translation_ids = {
        v["translation_id"] for v in votes_data if v.get("translation_id")
    }
    translations = (
        session.query(Translation).filter(Translation.id.in_(translation_ids)).all()
    )
    translation_map = {t.id: t for t in translations}

    for v1, v2 in combinations(votes_data, 2):
        t1 = translation_map.get(v1["translation_id"])
        t2 = translation_map.get(v2["translation_id"])

        if not t1 or not t2:
            continue

        r1, r2 = v1["rating"], v2["rating"]

        # Check tie-skip logic
        if _should_skip_pair(r1, r2):
            continue

        if r1 > r2:
            winner_model = str(t1.model)
            loser_model = str(t2.model)
            score = _gap_to_score(abs(r1 - r2))
        elif r2 > r1:
            winner_model = str(t2.model)
            loser_model = str(t1.model)
            score = _gap_to_score(abs(r1 - r2))
        else:
            # Equal ratings: tie (0.5) for 1-star and 2-star
            winner_model = None
            loser_model = None
            score = 0.5

        try:
            # Store comparison without incremental rating update;
            # ratings are rebuilt from all comparisons below.
            comp = PairwiseComparison(
                query_id=query_id,
                user_id=user_id,
                winner_model=winner_model,
                loser_model=loser_model,
                translation_a_id=v1["translation_id"],
                translation_b_id=v2["translation_id"],
                source="derived",
                score=score,
            )
            session.add(comp)
            session.flush()
        except Exception:
            logger.exception(
                "Error recording pairwise comparison for %s vs %s",
                t1.model,
                t2.model,
            )

    # Rebuild all ratings from stored comparisons to ensure consistency
    elo_service.rebuild_ratings_from_comparisons()
