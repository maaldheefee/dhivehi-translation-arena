"""Vote repository for database operations related to Vote model."""

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models import Vote


class VoteRepository:
    """Repository for Vote model database operations."""

    def __init__(self, db_session: Session):
        """Initialize repository with database session."""
        self.db_session = db_session

    def add(self, vote: Vote) -> Vote:
        """Add a new vote to the database."""
        self.db_session.add(vote)
        self.db_session.commit()
        return vote

    def bulk_add(self, votes: list[Vote]) -> None:
        """Add multiple votes to the database."""
        for vote in votes:
            self.db_session.add(vote)
        self.db_session.commit()

    def get_by_id(self, vote_id: int) -> Vote | None:
        """Get vote by ID."""
        return self.db_session.query(Vote).filter(Vote.id == vote_id).first()

    def get_by_user_and_query(self, user_id: int, query_id: int) -> list[Vote]:
        """Get all votes by user for a specific query."""
        return (
            self.db_session.query(Vote)
            .filter(and_(Vote.user_id == user_id, Vote.query_id == query_id))
            .all()
        )

    def get_by_user_query_and_translation(
        self, user_id: int, query_id: int, translation_id: int
    ) -> Vote | None:
        """Get vote by user, query, and translation."""
        return (
            self.db_session.query(Vote)
            .filter(
                and_(
                    Vote.user_id == user_id,
                    Vote.query_id == query_id,
                    Vote.translation_id == translation_id,
                )
            )
            .first()
        )

    def get_all(self) -> list[Vote]:
        """Get all votes."""
        return self.db_session.query(Vote).all()

    def delete_by_user_and_query(self, user_id: int, query_id: int) -> None:
        """Delete all votes by user for a specific query."""
        votes = self.get_by_user_and_query(user_id, query_id)
        for vote in votes:
            self.db_session.delete(vote)
        self.db_session.commit()

    def delete(self, vote: Vote) -> None:
        """Delete a vote."""
        self.db_session.delete(vote)
        self.db_session.commit()

    def update(self, vote: Vote) -> Vote:
        """Update an existing vote."""
        self.db_session.commit()
        return vote
