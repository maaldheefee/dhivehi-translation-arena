"""ELO rating service for pairwise comparison-based ranking.

This service manages ELO ratings for translation models, supporting both:
- Derived comparisons (inferred from star ratings)
- Explicit comparisons (from Quick Compare UI)
"""

import logging
from itertools import combinations
from typing import cast

from sqlalchemy.orm import Session

from app.database import db_session
from app.models import ModelELO, PairwiseComparison, Translation, Vote

logger = logging.getLogger(__name__)

# ELO constants
K_FACTOR = 32  # Higher K = faster convergence, good for low data volume
DEFAULT_ELO = 1500.0


class ELOService:
    """Service for managing ELO ratings and pairwise comparisons."""

    def __init__(self, session: Session | None = None):
        self.session = session or cast(Session, db_session)

    def get_or_create(self, model: str) -> ModelELO:
        """Get existing ELO record or create new one with default rating."""
        elo_record = (
            self.session.query(ModelELO).filter(ModelELO.model == model).first()
        )
        if not elo_record:
            elo_record = ModelELO(model=model, elo_rating=DEFAULT_ELO)
            self.session.add(elo_record)
            self.session.flush()
        return elo_record

    def update_ratings(self, winner: str, loser: str) -> tuple[float, float]:
        """Update ELO ratings after a match. Returns (new_winner_elo, new_loser_elo)."""
        winner_record = self.get_or_create(winner)
        loser_record = self.get_or_create(loser)

        # Calculate expected scores
        expected_winner = 1 / (
            1 + 10 ** ((loser_record.elo_rating - winner_record.elo_rating) / 400)
        )
        expected_loser = 1 - expected_winner

        # Update ratings
        winner_record.elo_rating += K_FACTOR * (1 - expected_winner)
        loser_record.elo_rating += K_FACTOR * (0 - expected_loser)

        # Update win/loss counters
        winner_record.wins = (winner_record.wins or 0) + 1
        loser_record.losses = (loser_record.losses or 0) + 1

        self.session.commit()

        return winner_record.elo_rating, loser_record.elo_rating

    def record_tie(self, model_a: str, model_b: str) -> tuple[float, float]:
        """Record a tie between two models. Ratings converge toward each other."""
        a_record = self.get_or_create(model_a)
        b_record = self.get_or_create(model_b)

        # For ties, each player scores 0.5
        expected_a = 1 / (1 + 10 ** ((b_record.elo_rating - a_record.elo_rating) / 400))

        a_record.elo_rating += K_FACTOR * (0.5 - expected_a)
        b_record.elo_rating += K_FACTOR * (0.5 - (1 - expected_a))

        a_record.ties = (a_record.ties or 0) + 1
        b_record.ties = (b_record.ties or 0) + 1

        self.session.commit()

        return a_record.elo_rating, b_record.elo_rating

    def record_comparison(
        self,
        query_id: int,
        user_id: int,
        winner_model: str | None,
        loser_model: str | None,
        translation_a_id: int | None = None,
        translation_b_id: int | None = None,
        source: str = "explicit",
    ) -> PairwiseComparison:
        """Record a pairwise comparison and update ELO ratings."""
        comparison = PairwiseComparison(
            query_id=query_id,
            user_id=user_id,
            winner_model=winner_model,
            loser_model=loser_model,
            translation_a_id=translation_a_id,
            translation_b_id=translation_b_id,
            source=source,
        )
        self.session.add(comparison)

        # Update ELO based on result
        if winner_model and loser_model:
            self.update_ratings(winner_model, loser_model)
        elif translation_a_id and translation_b_id and not winner_model:
            # It's a tie - get model names from translations
            t_a = self.session.query(Translation).get(translation_a_id)
            t_b = self.session.query(Translation).get(translation_b_id)
            if t_a and t_b:
                self.record_tie(t_a.model, t_b.model)

        return comparison

    def get_all_rankings(self) -> list[dict]:
        """Get all models ranked by ELO rating."""
        records = (
            self.session.query(ModelELO).order_by(ModelELO.elo_rating.desc()).all()
        )
        return [
            {
                "model": r.model,
                "elo_rating": r.elo_rating,
                "wins": r.wins or 0,
                "losses": r.losses or 0,
                "ties": r.ties or 0,
                "total_matches": r.total_matches,
                "win_rate": r.win_rate,
            }
            for r in records
        ]

    def derive_from_existing_votes(self, user_id: int | None = None) -> int:
        """
        Derive pairwise comparisons from existing star rating votes.

        This is a one-time migration function that:
        1. Groups votes by query_id and user_id
        2. For each pair of votes on the same query, compares ratings
        3. Records winner/loser based on rating difference

        Returns the number of comparisons derived.
        """
        # Get all votes grouped by query
        votes = self.session.query(Vote).all()

        # Group by (query_id, user_id)
        vote_groups: dict[tuple[int, int], list[Vote]] = {}
        for vote in votes:
            key = (int(vote.query_id), int(vote.user_id))
            if key not in vote_groups:
                vote_groups[key] = []
            vote_groups[key].append(vote)

        comparisons_created = 0

        for (query_id, uid), group_votes in vote_groups.items():
            if len(group_votes) < 2:
                continue

            # Check if we should filter by user_id
            if user_id is not None and uid != user_id:
                continue

            # Create pairwise comparisons for all pairs
            for v1, v2 in combinations(group_votes, 2):
                if v1.rating is None or v2.rating is None:
                    continue

                # Check if this comparison already exists
                existing = (
                    self.session.query(PairwiseComparison)
                    .filter(
                        PairwiseComparison.query_id == query_id,
                        PairwiseComparison.user_id == uid,
                        PairwiseComparison.translation_a_id == v1.translation_id,
                        PairwiseComparison.translation_b_id == v2.translation_id,
                        PairwiseComparison.source == "derived",
                    )
                    .first()
                )
                if existing:
                    continue

                # Get model names from translations
                t1 = self.session.query(Translation).get(v1.translation_id)
                t2 = self.session.query(Translation).get(v2.translation_id)
                if not t1 or not t2:
                    continue

                winner_model = None
                loser_model = None

                if v1.rating > v2.rating:
                    winner_model = t1.model
                    loser_model = t2.model
                elif v2.rating > v1.rating:
                    winner_model = t2.model
                    loser_model = t1.model
                # Equal ratings = tie (winner_model and loser_model stay None)

                self.record_comparison(
                    query_id=query_id,
                    user_id=uid,
                    winner_model=winner_model,
                    loser_model=loser_model,
                    translation_a_id=v1.translation_id,
                    translation_b_id=v2.translation_id,
                    source="derived",
                )
                comparisons_created += 1

        logger.info(f"Derived {comparisons_created} pairwise comparisons from votes")
        return comparisons_created


def get_elo_service(session: Session | None = None) -> ELOService:
    """Factory function to get ELO service instance."""
    return ELOService(session)
