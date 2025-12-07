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


def process_votes(user_id, query_id, votes_data):
    """
    Process votes for a query from a user.

    Args:
        user_id (int): The ID of the user casting votes
        query_id (int): The ID of the query being voted on
        votes_data (list): List of vote dictionaries with keys:
            - translation_id (int): ID of the translation being voted on
            - rating (int): Rating value (3=Excellent, 2=Good, 1=Okay, -1=Rejected)

    Returns:
        dict: Result of the voting process
    """
    session = cast(Session, db_session)
    vote_repo = VoteRepository(session)

    try:
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

            # Check if vote already exists
            existing_vote = vote_repo.get_by_user_query_and_translation(
                user_id, query_id, translation_id
            )

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


def _derive_pairwise_from_votes(session, user_id, query_id, votes_data):
    """
    Derive pairwise comparisons from star rating votes.

    For each pair of votes on the same query, if one rating is higher,
    record it as a win for that model.
    """
    elo_service = get_elo_service(session)

    for v1, v2 in combinations(votes_data, 2):
        t1 = session.query(Translation).get(v1["translation_id"])
        t2 = session.query(Translation).get(v2["translation_id"])

        if not t1 or not t2:
            continue

        r1, r2 = v1["rating"], v2["rating"]
        winner_model = None
        loser_model = None

        if r1 > r2:
            winner_model = t1.model
            loser_model = t2.model
        elif r2 > r1:
            winner_model = t2.model
            loser_model = t1.model
        # Equal ratings = tie (winner and loser stay None)

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
