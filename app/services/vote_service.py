"""Vote service for processing hybrid voting system votes."""

import logging
from itertools import combinations
from typing import cast

from sqlalchemy.orm import Session

from app.database import db_session
from app.models import Translation, Vote
from app.repositories.vote_repository import VoteRepository
from app.services.elo_service import get_elo_service

logger = logging.getLogger(__name__)


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

        # Derive pairwise comparisons from the votes just submitted
        if len(processed_votes) >= 2:
            _derive_pairwise_from_votes(session, user_id, query_id, processed_votes)

    except Exception:
        logger.exception("Error processing votes")
        return {"success": False, "error": "An error occurred while processing votes"}

    else:
        return {"success": True, "message": "Votes processed successfully"}


def _derive_pairwise_from_votes(
    session: Session, user_id, query_id, votes_data
) -> None:
    """
    Derive pairwise comparisons from star rating votes.

    For each pair of votes on the same query, if one rating is higher,
    record it as a win for that model.
    """
    elo_service = get_elo_service(session)

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
        winner_model = None
        loser_model = None

        if r1 > r2:
            winner_model = str(t1.model)
            loser_model = str(t2.model)
        elif r2 > r1:
            winner_model = str(t2.model)
            loser_model = str(t1.model)
        else:
            # r1 == r2 -> tie
            if r1 == 3:
                # Both achieved perfection; this is a measure of query ease,
                # not comparative skill. Do not record a tie.
                continue

            # Both struggled equally (e.g., both got 1 star or 2 stars). A tie.
            winner_model = None
            loser_model = None

        try:
            elo_service.record_comparison(
                query_id=query_id,
                user_id=user_id,
                winner_model=winner_model,
                loser_model=loser_model,
                translation_a_id=v1["translation_id"],
                translation_b_id=v2["translation_id"],
                source="derived",
            )
        except Exception:
            logger.exception(
                f"Error recording pairwise comparison for {t1.model} vs {t2.model}"
            )
