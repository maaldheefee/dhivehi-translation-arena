#!/usr/bin/env python3
"""Database initialization script for Docker container."""

import os
from pathlib import Path

# Note: In Docker, environment variables are already loaded

# Import Flask app and database components
from app import create_app
from app.database import db_session
from app.models import Base, User
from app.services.user_service import create_user
from app import database

def main():
    """Initialize the database with schema and default users."""
    print("Starting database initialization...")
    
    # Create Flask app instance
    app = create_app()
    
    with app.app_context():
        # Ensure data directory exists
        Path("data").mkdir(parents=True, exist_ok=True)
        print("Data directory created/verified.")

        # Create database schema
        print("Creating database schema...")
        Base.metadata.create_all(bind=database.engine, checkfirst=True)
        print("Database schema created successfully.")

        # Create default users if none exist
        default_users = [
            {"username": "Hassaan", "password": "1234", "is_admin": True},
            {"username": "John", "password": "1234", "is_admin": False},
        ]

        user_count = db_session.query(User).count()
        if user_count == 0:
            print("No users found, creating default users...")
            for user_data in default_users:
                create_user(
                    username=user_data["username"],
                    password=user_data["password"],
                    is_admin=user_data["is_admin"],
                )
            print("Default users created successfully!")
        else:
            print(f"{user_count} users already exist, skipping default user creation.")

        print("Database initialization completed successfully!")

if __name__ == "__main__":
    main()
