"""Query repository for database operations related to Query model."""

from sqlalchemy.orm import Session

from app.models import Query


class QueryRepository:
    """Repository for Query model database operations."""

    def __init__(self, db_session: Session):
        """Initialize repository with database session."""
        self.db_session = db_session

    def add(self, query: Query) -> Query:
        """Add a new query to the database."""
        self.db_session.add(query)
        self.db_session.commit()
        return query

    def get_by_id(self, query_id: int) -> Query | None:
        """Get query by ID."""
        return self.db_session.query(Query).filter(Query.id == query_id).first()

    def get_by_source_text(self, source_text: str) -> Query | None:
        """Get query by source text."""
        return (
            self.db_session.query(Query)
            .filter(Query.source_text == source_text)
            .first()
        )

    def get_all(self) -> list[Query]:
        """Get all queries."""
        return self.db_session.query(Query).all()

    def create_if_not_exists(self, source_text: str) -> Query:
        """Create a new query if it doesn't exist, otherwise return existing."""
        query = self.get_by_source_text(source_text)
        if not query:
            query = Query(source_text=source_text)
            self.db_session.add(query)
            self.db_session.commit()
        return query

    def update(self, query: Query) -> Query:
        """Update an existing query."""
        self.db_session.commit()
        return query

    def delete(self, query: Query) -> None:
        """Delete a query."""
        self.db_session.delete(query)
        self.db_session.commit()
