"""Vote service for processing hybrid voting system votes."""

import logging

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
    vote_repo = VoteRepository(db_session)

    try:
        # Remove existing votes for this user and query
        vote_repo.delete_by_user_and_query(user_id, query_id)

        # Create new votes
        new_votes = []
        for vote_data in votes_data:
            translation_id = vote_data.get("translation_id")
            rating = vote_data.get("rating")

            # Validate data
            if not translation_id:
                continue

            # Validate rating value
            if rating not in [3, 2, 1, -1]:
                continue

            vote = Vote(
                user_id=user_id,
                query_id=query_id,
                translation_id=translation_id,
                rating=rating,
            )
            new_votes.append(vote)

        if new_votes:
            vote_repo.bulk_add(new_votes)

        return {"success": True, "message": "Votes processed successfully"}

    except Exception:
        logger.exception("Error processing votes")
        return {"success": False, "error": "An error occurred while processing votes"}
