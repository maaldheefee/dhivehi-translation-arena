from typing import cast

from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import db_session
from app.models import User
from app.repositories.user_repository import UserRepository


def create_user(username, password, *, is_admin=False):
    """
    Creates a new user with the given credentials.
    Returns the created user object or None if creation fails.
    """
    if not username or not password:
        return None

    session = cast(Session, db_session)
    user_repo = UserRepository(session)

    if user_repo.exists_by_username(username):
        return None

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        is_admin=is_admin,
    )

    try:
        return user_repo.add(user)
    except Exception:
        return None


def get_user_by_username(username):
    """Retrieves a user by username."""
    session = cast(Session, db_session)
    user_repo = UserRepository(session)
    return user_repo.get_by_username(username)


def check_password(user, password):
    """Verifies if the provided password matches the user's password."""
    if not user or not password:
        return False
    return check_password_hash(user.password_hash, password)


def delete_user(username):
    """Deletes a user by username."""
    session = cast(Session, db_session)
    user_repo = UserRepository(session)
    user = user_repo.get_by_username(username)
    if user:
        session.delete(user)
        session.commit()
        return True
    return False
