#!/usr/bin/env python3
"""Database initialization script for Docker container."""

import os
from pathlib import Path

# Note: In Docker, environment variables are already loaded
# Import Flask app and database components
from app import create_app, database
from app.database import db_session
from app.models import Base, ModelELO, PairwiseComparison, User
from app.services.user_service import create_user


def main():
    """Initialize the database with schema and default users."""
    print("Starting database initialization...")

    # Create Flask app instance
    app = create_app()

    with app.app_context():
        # Ensure data directory exists
        Path("data").mkdir(parents=True, exist_ok=True)
        print("Data directory created/verified.")

        # Create database schema (including new ELO tables)
        print("Creating database schema...")
        Base.metadata.create_all(bind=database.engine, checkfirst=True)
        print("Database schema created successfully.")

        # Create default users if none exist
        default_users = [
            # Default admin - set INIT_ADMIN_PASSWORD env var or change password immediately after first login
            {
                "username": "admin",
                "password": os.environ.get("INIT_ADMIN_PASSWORD", "changeme"),
                "is_admin": True,
            },
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

        # Run ELO migration if needed
        _migrate_elo_data()

        print("Database initialization completed successfully!")


def _migrate_elo_data():
    """Derive pairwise comparisons and ELO ratings from existing star ratings."""
    # Check if we already have ELO data
    existing_comparisons = db_session.query(PairwiseComparison).count()
    existing_elo = db_session.query(ModelELO).count()

    if existing_comparisons > 0 or existing_elo > 0:
        print(
            f"ELO data already exists ({existing_comparisons} comparisons, "
            f"{existing_elo} model ratings). Skipping migration."
        )
        return

    print("Deriving ELO ratings from existing star ratings...")

    # Import here to avoid circular imports during app startup
    from app.services.elo_service import get_elo_service  # noqa: PLC0415

    elo_service = get_elo_service()
    comparisons_created = elo_service.derive_from_existing_votes()

    if comparisons_created > 0:
        print(
            f"Created {comparisons_created} pairwise comparisons from existing votes."
        )

        # Get final ELO standings
        rankings = elo_service.get_all_rankings()
        print("\nInitial ELO Rankings:")
        for i, r in enumerate(rankings, 1):
            print(
                f"  {i}. {r['model']}: {r['elo_rating']:.0f} ELO "
                f"({r['wins']}W/{r['losses']}L/{r['ties']}T)"
            )
    else:
        print("No existing votes found to derive comparisons from.")


if __name__ == "__main__":
    main()
