"""User repository for database operations related to User model."""

from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    """Repository for User model database operations."""

    def __init__(self, db_session: Session):
        """Initialize repository with database session."""
        self.db_session = db_session

    def add(self, user: User) -> User:
        """Add a new user to the database."""
        self.db_session.add(user)
        self.db_session.commit()
        return user

    def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        return self.db_session.query(User).filter(User.username == username).first()

    def get_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        return self.db_session.query(User).filter(User.id == user_id).first()

    def get_all(self):
        """Get all users."""
        return self.db_session.query(User).all()

    def exists_by_username(self, username: str) -> bool:
        """Check if a user with given username exists."""
        return (
            self.db_session.query(User).filter(User.username == username).first()
            is not None
        )

    def update(self, user: User) -> User:
        """Update an existing user."""
        self.db_session.commit()
        return user

    def delete(self, user: User) -> None:
        """Delete a user."""
        self.db_session.delete(user)
        self.db_session.commit()
