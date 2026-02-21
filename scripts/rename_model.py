#!/usr/bin/env python3
"""
Database migration script to rename a model across all tables.

This script updates model references in:
- translations.model
- pairwise_comparisons.winner_model
- pairwise_comparisons.loser_model
- model_elo.model

Usage:
    python scripts/rename_model.py <old_name> <new_name> [--dry-run]

Example:
    python scripts/rename_model.py "gemini-3-flash-t1.0" "gemini-3-flash-default-t1.0" --dry-run
    python scripts/rename_model.py "gemini-3-flash-t1.0" "gemini-3-flash-default-t1.0"
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.models import ModelELO, PairwiseComparison, Translation

# Create standalone database connection
database_uri = f"sqlite:///{Config.DATA_DIR}/dhivehi_translation_arena.db"
engine = create_engine(database_uri)
Session = sessionmaker(bind=engine)


def count_references(session, old_name: str) -> dict[str, int]:
    """Count how many records reference the old model name."""
    counts = {}

    # Count translations
    counts["translations"] = (
        session.query(Translation).filter(Translation.model == old_name).count()
    )

    # Count pairwise comparisons (winner)
    counts["comparisons_winner"] = (
        session.query(PairwiseComparison)
        .filter(PairwiseComparison.winner_model == old_name)
        .count()
    )

    # Count pairwise comparisons (loser)
    counts["comparisons_loser"] = (
        session.query(PairwiseComparison)
        .filter(PairwiseComparison.loser_model == old_name)
        .count()
    )

    # Count ELO records
    counts["elo_records"] = (
        session.query(ModelELO).filter(ModelELO.model == old_name).count()
    )

    return counts


def check_new_name_exists(session, new_name: str) -> dict[str, bool]:
    """Check if the new name already exists in any table."""
    exists = {}

    exists["translations"] = (
        session.query(Translation).filter(Translation.model == new_name).first()
        is not None
    )

    exists["comparisons"] = (
        session.query(PairwiseComparison)
        .filter(
            (PairwiseComparison.winner_model == new_name)
            | (PairwiseComparison.loser_model == new_name)
        )
        .first()
        is not None
    )

    exists["elo_records"] = (
        session.query(ModelELO).filter(ModelELO.model == new_name).first() is not None
    )

    return exists


def rename_model(old_name: str, new_name: str, dry_run: bool = True) -> bool:
    """
    Rename a model across all database tables.

    Args:
        old_name: Current model identifier
        new_name: New model identifier
        dry_run: If True, only show what would be changed without committing

    Returns:
        True if successful, False otherwise
    """
    session = Session()

    print(f"\n{'=' * 60}")
    print(f"Model Rename Migration: '{old_name}' → '{new_name}'")
    print(
        f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE (changes will be committed)'}"
    )
    print(f"{'=' * 60}\n")

    # Step 1: Count existing references
    print("Step 1: Counting existing references...")
    counts = count_references(session, old_name)

    total_refs = sum(counts.values())
    if total_refs == 0:
        print(f"❌ No references found for model '{old_name}'")
        session.close()
        return False

    print(f"Found {total_refs} total references:")
    for table, count in counts.items():
        if count > 0:
            print(f"  - {table}: {count}")

    # Step 2: Check if new name already exists
    print("\nStep 2: Checking for conflicts...")
    conflicts = check_new_name_exists(session, new_name)

    if any(conflicts.values()):
        print(f"⚠️  WARNING: New name '{new_name}' already exists in:")
        for table, exists in conflicts.items():
            if exists:
                print(f"  - {table}")

        response = input(
            "\nThis will merge data from both models. Continue? (yes/no): "
        )
        if response.lower() != "yes":
            print("❌ Migration cancelled by user")
            session.close()
            return False
    else:
        print(f"✓ No conflicts found - '{new_name}' is available")

    # Step 3: Perform the migration
    print("\nStep 3: Updating database records...")

    try:
        # Update translations
        if counts["translations"] > 0:
            print(f"  Updating {counts['translations']} translation records...")
            if not dry_run:
                session.query(Translation).filter(Translation.model == old_name).update(
                    {Translation.model: new_name}
                )

        # Update pairwise comparisons (winner)
        if counts["comparisons_winner"] > 0:
            print(
                f"  Updating {counts['comparisons_winner']} comparison records (winner)..."
            )
            if not dry_run:
                session.query(PairwiseComparison).filter(
                    PairwiseComparison.winner_model == old_name
                ).update({PairwiseComparison.winner_model: new_name})

        # Update pairwise comparisons (loser)
        if counts["comparisons_loser"] > 0:
            print(
                f"  Updating {counts['comparisons_loser']} comparison records (loser)..."
            )
            if not dry_run:
                session.query(PairwiseComparison).filter(
                    PairwiseComparison.loser_model == old_name
                ).update({PairwiseComparison.loser_model: new_name})

        # Update or merge ELO records
        if counts["elo_records"] > 0:
            print(f"  Updating {counts['elo_records']} ELO record(s)...")
            if not dry_run:
                old_elo = (
                    session.query(ModelELO).filter(ModelELO.model == old_name).first()
                )

                new_elo = (
                    session.query(ModelELO).filter(ModelELO.model == new_name).first()
                )

                if new_elo and old_elo:
                    # Merge ELO records
                    print("    Merging ELO data:")
                    print(
                        f"      Old: {old_elo.elo_rating:.1f} ({old_elo.wins}W/{old_elo.losses}L/{old_elo.ties}T)"
                    )
                    print(
                        f"      New: {new_elo.elo_rating:.1f} ({new_elo.wins}W/{new_elo.losses}L/{new_elo.ties}T)"
                    )

                    # Combine statistics
                    new_elo.wins = (new_elo.wins or 0) + (old_elo.wins or 0)
                    new_elo.losses = (new_elo.losses or 0) + (old_elo.losses or 0)
                    new_elo.ties = (new_elo.ties or 0) + (old_elo.ties or 0)

                    # Average the ELO ratings weighted by total matches
                    old_matches = old_elo.total_matches
                    new_matches = new_elo.total_matches
                    total_matches = old_matches + new_matches

                    if total_matches > 0:
                        new_elo.elo_rating = (
                            old_elo.elo_rating * old_matches
                            + new_elo.elo_rating * new_matches
                        ) / total_matches

                    print(
                        f"      Merged: {new_elo.elo_rating:.1f} ({new_elo.wins}W/{new_elo.losses}L/{new_elo.ties}T)"
                    )

                    # Delete old record
                    session.delete(old_elo)
                elif old_elo:
                    # Just rename
                    old_elo.model = new_name

        if dry_run:
            print("\n✓ Dry run completed - no changes were made")
            session.rollback()
        else:
            session.commit()
            print("\n✓ Migration completed successfully!")
            print(
                f"\n⚠️  IMPORTANT: Update config.py to rename the model key from '{old_name}' to '{new_name}'"
            )

        session.close()
        return True

    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        session.rollback()
        session.close()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Rename a model across all database tables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (safe, shows what would change)
  python scripts/rename_model.py "old-model-name" "new-model-name" --dry-run

  # Actually perform the rename
  python scripts/rename_model.py "old-model-name" "new-model-name"

  # Rename a Gemini model
  python scripts/rename_model.py "gemini-3-flash-t1.0" "gemini-3-flash-default"
        """,
    )

    parser.add_argument("old_name", help="Current model identifier")
    parser.add_argument("new_name", help="New model identifier")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without committing",
    )

    args = parser.parse_args()

    # Confirm if not dry run
    if not args.dry_run:
        print("\n⚠️  WARNING: This will modify the database!")
        print(f"Old name: {args.old_name}")
        print(f"New name: {args.new_name}")
        response = input("\nAre you sure you want to proceed? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Migration cancelled")
            return

    success = rename_model(args.old_name, args.new_name, args.dry_run)

    if success and not args.dry_run:
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. Update app/config.py:")
        print(f"   - Rename the key '{args.old_name}' to '{args.new_name}'")
        print("   - Keep all other configuration the same")
        print("\n2. Restart the application")
        print("\n3. Verify the changes in the UI")
        print("=" * 60)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
