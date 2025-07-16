from pathlib import Path

from app.database import DATABASE_URI, db_session, engine
from app.models import Base
from app.services.user_service import create_user

# Default users configuration
DEFAULT_USERS = [
    {"username": "Hassaan", "password": "1234", "is_admin": True},
    {"username": "Ashraaf", "password": "1234", "is_admin": False},
]

# Ensure the data directory exists
Path("data").mkdir(parents=True, exist_ok=True)

# If using SQLite, delete the database file to ensure clean schema creation
if DATABASE_URI.startswith("sqlite:///"):
    db_path = DATABASE_URI.replace("sqlite:///", "")
    if Path(db_path).exists():
        Path(db_path).unlink()
        print(f"Deleted existing database file: {db_path}")

# Create all tables with the updated schema
Base.metadata.create_all(engine)
print("Database initialized successfully with new schema!")

# Create default users if database is empty
from app.models import User
user_count = db_session.query(User).count()
if user_count == 0:
    for user_data in DEFAULT_USERS:
        create_user(
            username=user_data["username"],
            password=user_data["password"],
            is_admin=user_data["is_admin"],
        )
    print("Default users created successfully!")
else:
    print("Users already exist, skipping default user creation.")
