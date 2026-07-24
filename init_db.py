#!/usr/bin/env python3
"""Database initialization script for Docker container."""

import os
from pathlib import Path

from sqlalchemy import inspect, text

# Note: In Docker, environment variables are already loaded
# Import Flask app and database components
from app import create_app, database
from app.database import Base, db_session
from app.models import ModelELO, PairwiseComparison, User
from app.services.user_service import create_user


def main() -> None:
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
        if database.engine is None:
            msg = "Database engine is not initialized. Ensure init_db(app) was called."
            raise RuntimeError(msg)
        Base.metadata.create_all(bind=database.engine, checkfirst=True)
        print("Database schema created successfully.")

        # Run idempotent schema migration for Glicko-2 columns
        _migrate_glicko2_columns(database.engine)

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


def _migrate_glicko2_columns(engine) -> None:
    """Idempotent migration: add Glicko-2 columns to existing tables if missing.

    Checks for column existence via inspect() and adds missing columns
    with ALTER TABLE. Always runs backfill for NULL values to ensure
    resumability — a failed previous run can leave columns added but
    values unpopulated.
    """
    inspector = inspect(engine)

    # --- ModelELO: add rating_deviation, volatility, legacy_elo_rating, last_comparison_at ---
    elo_columns = {col["name"] for col in inspector.get_columns("model_elo")}

    new_elo_columns = [
        ("rating_deviation", "FLOAT DEFAULT 350.0"),
        ("volatility", "FLOAT DEFAULT 0.06"),
        ("legacy_elo_rating", "FLOAT"),
        ("last_comparison_at", "DATETIME"),
    ]

    for col_name, col_def in new_elo_columns:
        if col_name not in elo_columns:
            print(f"  Adding column '{col_name}' to model_elo...")
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE model_elo ADD COLUMN {col_name} {col_def}"))

    # Always backfill NULL values (idempotent — safe to run every startup)
    with engine.begin() as conn:
        conn.execute(text("UPDATE model_elo SET legacy_elo_rating = elo_rating WHERE legacy_elo_rating IS NULL"))
        conn.execute(text("UPDATE model_elo SET rating_deviation = 350.0 WHERE rating_deviation IS NULL"))
        conn.execute(text("UPDATE model_elo SET volatility = 0.06 WHERE volatility IS NULL"))
    # Backfill NULL win/loss/tie counters (columns existed before but were nullable)
    with engine.begin() as conn:
        conn.execute(text("UPDATE model_elo SET wins = 0 WHERE wins IS NULL"))
        conn.execute(text("UPDATE model_elo SET losses = 0 WHERE losses IS NULL"))
        conn.execute(text("UPDATE model_elo SET ties = 0 WHERE ties IS NULL"))
    print("  Backfilled Glicko-2 columns on model_elo.")

    # --- PairwiseComparison: add score column ---
    comp_columns = {col["name"] for col in inspector.get_columns("pairwise_comparisons")}

    if "score" not in comp_columns:
        print("  Adding column 'score' to pairwise_comparisons...")
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE pairwise_comparisons ADD COLUMN score FLOAT"))

    # Always backfill NULL scores (idempotent — safe to run every startup)
    # - Non-null winner/loser -> 1.0 (decisive win)
    # - Null winner/loser with both translation IDs -> 0.5 (tie)
    # - Rows missing translation IDs are left untouched (incomplete/corrupt)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE pairwise_comparisons SET score = 1.0 "
                "WHERE winner_model IS NOT NULL AND loser_model IS NOT NULL "
                "AND score IS NULL"
            )
        )
        conn.execute(
            text(
                "UPDATE pairwise_comparisons SET score = 0.5 "
                "WHERE winner_model IS NULL AND loser_model IS NULL "
                "AND translation_a_id IS NOT NULL "
                "AND translation_b_id IS NOT NULL "
                "AND score IS NULL"
            )
        )
    print("  Backfilled score column on pairwise_comparisons.")


def _migrate_elo_data() -> None:
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
    from app.services.elo_service import get_elo_service

    elo_service = get_elo_service()
    comparisons_created = elo_service.derive_from_existing_votes()

    if comparisons_created > 0:
        print(f"Created {comparisons_created} pairwise comparisons from existing votes.")

        # Get final ELO standings
        rankings = elo_service.get_all_rankings()
        print("\nInitial ELO Rankings:")
        for i, r in enumerate(rankings, 1):
            print(f"  {i}. {r['model']}: {r['elo_rating']:.0f} ELO ({r['wins']}W/{r['losses']}L/{r['ties']}T)")
    else:
        print("No existing votes found to derive comparisons from.")


if __name__ == "__main__":
    main()
