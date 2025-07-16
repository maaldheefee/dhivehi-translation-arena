"""Translation repository for database operations related to Translation model."""

from sqlalchemy.orm import Session

from app.models import Translation


class TranslationRepository:
    """Repository for Translation model database operations."""

    def __init__(self, db_session: Session):
        """Initialize repository with database session."""
        self.db_session = db_session

    def add(self, translation: Translation) -> Translation:
        """Add a new translation to the database."""
        self.db_session.add(translation)
        self.db_session.commit()
        return translation

    def get_by_id(self, translation_id: int) -> Translation | None:
        """Get translation by ID."""
        return (
            self.db_session.query(Translation)
            .filter(Translation.id == translation_id)
            .first()
        )

    def get_by_query_and_model(self, query_id: int, model: str) -> Translation | None:
        """Get translation by query ID and model."""
        return (
            self.db_session.query(Translation)
            .filter(Translation.query_id == query_id, Translation.model == model)
            .first()
        )

    def get_by_query_id(self, query_id: int) -> list[Translation]:
        """Get all translations for a query."""
        return (
            self.db_session.query(Translation)
            .filter(Translation.query_id == query_id)
            .all()
        )

    def get_all(self) -> list[Translation]:
        """Get all translations."""
        return self.db_session.query(Translation).all()

    def update(self, translation: Translation) -> Translation:
        """Update an existing translation."""
        self.db_session.commit()
        return translation

    def delete(self, translation: Translation) -> None:
        """Delete a translation."""
        self.db_session.delete(translation)
        self.db_session.commit()
