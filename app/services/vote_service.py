"""Vote service for processing hybrid voting system votes."""

import logging
from typing import cast

from sqlalchemy.orm import Session

from app.database import db_session
from app.models import Vote
from app.repositories.vote_repository import VoteRepository

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
            else:
                vote = Vote(
                    user_id=user_id,
                    query_id=query_id,
                    translation_id=translation_id,
                    rating=rating,
                )
                vote_repo.add(vote)  # Add immediately or collect for bulk?
                # Bulk add is more efficient but mixing updates and adds is tricky with bulk_add checks
                # So just adding one by one is safer for now given checking requirement.
                # Actually, can't bulk add if we need to check existence for each.

        # We process one by one, so no bulk_add at end.

    except Exception:
        logger.exception("Error processing votes")
        return {"success": False, "error": "An error occurred while processing votes"}

    else:
        return {"success": True, "message": "Votes processed successfully"}
