"""Glicko-2 rating service for pairwise comparison-based ranking.

This service manages Glicko-2 ratings for translation models, supporting both:
- Derived comparisons (inferred from star ratings with fractional scores)
- Explicit comparisons (from Quick Compare UI, binary scores)
"""

import logging
import math
from datetime import UTC, datetime
from itertools import combinations
from typing import cast

from sqlalchemy.orm import Session

from app.config import Config
from app.database import db_session
from app.models import ModelELO, PairwiseComparison, Translation, Vote

logger = logging.getLogger(__name__)

DEFAULT_ELO = Config.DEFAULT_RATING


def _as_utc(value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime without changing the instant."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _weeks_between(last_observed_at: datetime | None, observed_at: datetime) -> float:
    """Calculate non-negative elapsed weeks using an explicit observation clock."""
    if last_observed_at is None:
        return 0.0
    delta = _as_utc(observed_at) - _as_utc(last_observed_at)
    return max(0.0, delta.total_seconds() / (7 * 24 * 3600))


def _serialize_rating_state(records: list[ModelELO]) -> tuple[tuple, ...]:
    """Create a stable snapshot suitable for deterministic rebuild checks."""
    return tuple(
        (
            record.model,
            record.elo_rating,
            record.rating_deviation,
            record.volatility,
            record.legacy_elo_rating,
            record.last_comparison_at,
            record.wins,
            record.losses,
            record.ties,
        )
        for record in sorted(records, key=lambda item: item.model)
    )


def _glicko2_update(
    rating: float,
    rd: float,
    vol: float,
    opp_ratings: list[float],
    opp_rds: list[float],
    scores: list[float],
    weights: list[float] | None = None,
    tau: float = Config.GLICKO_TAU,
    c_per_week: float = Config.GLICKO_C_PER_WEEK,
    weeks_inactive: float = 0.0,
) -> tuple[float, float, float]:
    """Core Glicko-2 update for a single player vs multiple opponents.

    Args:
        rating: Player's current rating (µ, on Glicko-2 scale)
        rd: Player's current RD (φ, on Glicko-2 scale)
        vol: Player's current volatility (sigma)
        opp_ratings: Opponent ratings (Glicko-2 scale)
        opp_rds: Opponent RDs (Glicko-2 scale)
        scores: Game scores [0, 1] for each opponent
        tau: System constant
        c_per_week: RD time decay constant
        weeks_inactive: Weeks since last comparison

    Returns:
        (new_rating, new_rd, new_volatility) on Glicko-2 scale.
    """
    if weights is None:
        weights = [1.0] * len(scores)
    if not (len(opp_ratings) == len(opp_rds) == len(scores) == len(weights)):
        msg = "Opponent ratings, RDs, scores, and weights must have equal lengths"
        raise ValueError(msg)
    if any(weight <= 0 for weight in weights):
        msg = "Evidence weights must be positive"
        raise ValueError(msg)

    # Step 1: Apply time-based RD increase for inactivity
    if weeks_inactive > 0:
        rd = math.sqrt(rd**2 + (c_per_week**2) * weeks_inactive)

    # Step 2: Convert to Glicko-2 internal scale
    mu = (rating - 1500) / 173.7178
    phi = rd / 173.7178
    sigma = vol

    # Step 3: Compute g(phi_j) and E(mu, mu_j, phi_j) for each opponent
    def g(phi_j: float) -> float:
        return 1.0 / math.sqrt(1.0 + 3.0 * phi_j**2 / math.pi**2)

    def expected(mu: float, mu_j: float, phi_j: float) -> float:
        return 1.0 / (1.0 + math.exp(-g(phi_j) * (mu - mu_j)))

    if not opp_ratings:
        # No games: only apply RD time decay (already done above)
        new_phi = phi
        new_mu = mu
        new_sigma = sigma
    else:
        mu_js = [(r - 1500) / 173.7178 for r in opp_ratings]
        phi_js = [r / 173.7178 for r in opp_rds]

        # Step 4: Compute v (estimated variance)
        v_inv = sum(
            weight * g(pj) ** 2 * expected(mu, mj, pj) * (1 - expected(mu, mj, pj))
            for mj, pj, weight in zip(mu_js, phi_js, weights, strict=True)
        )
        v = 1.0 / v_inv if v_inv > 0 else 1e6

        # Step 5: Compute Δ (improvement)
        delta_sum = sum(
            weight * g(pj) * (s - expected(mu, mj, pj))
            for mj, pj, s, weight in zip(mu_js, phi_js, scores, weights, strict=True)
        )
        delta = v * delta_sum

        # Step 6: Compute new volatility (iterative)
        a = math.log(sigma**2)
        tau_sq = tau**2

        def f(x: float) -> float:
            ex = math.exp(x)
            num = ex * (delta**2 - phi**2 - v - ex)
            den = 2.0 * (phi**2 + v + ex) ** 2
            return num / den - (x - a) / tau_sq

        # Initial bounds
        A = a
        if delta**2 > phi**2 + v:
            B = math.log(delta**2 - phi**2 - v)
        else:
            k = 1.0
            while f(a - k * tau) < 0:
                k += 1
            B = a - k * tau

        fA = f(A)
        fB = f(B)
        while abs(B - A) > 1e-6:
            C = A + (A - B) * fA / (fB - fA)
            fC = f(C)
            if fC * fB <= 0:
                A = B
                fA = fB
            else:
                fA = fA / 2.0
            B = C
            fB = fC

        new_sigma = math.exp(A / 2.0)

        # Step 7: Compute new phi* (pre-rating-period)
        phi_star = math.sqrt(phi**2 + new_sigma**2)

        # Step 8: Compute new phi and mu
        new_phi = 1.0 / math.sqrt(1.0 / phi_star**2 + 1.0 / v)
        new_mu = mu + new_phi**2 * delta_sum

    # Step 9: Convert back to original scale
    new_rating = 173.7178 * new_mu + 1500
    new_rd = 173.7178 * new_phi

    # Apply MIN_RD floor
    new_rd = max(new_rd, Config.GLICKO_MIN_RD)

    return new_rating, new_rd, new_sigma


class ELOService:
    """Service for managing Glicko-2 ratings and pairwise comparisons."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session or cast(Session, db_session)

    def get_or_create(self, model: str) -> ModelELO:
        """Get existing rating record or create new one with default Glicko-2 values."""
        record = self.session.query(ModelELO).filter(ModelELO.model == model).first()
        if not record:
            record = ModelELO(
                model=model,
                elo_rating=DEFAULT_ELO,
                rating_deviation=Config.GLICKO_INITIAL_RD,
                volatility=Config.GLICKO_INITIAL_VOLATILITY,
            )
            self.session.add(record)
            self.session.flush()
        return record

    def _weeks_since_last_comparison(self, record: ModelELO, observed_at: datetime | None = None) -> float:
        """Calculate weeks since last comparison for RD time decay."""
        return _weeks_between(record.last_comparison_at, observed_at or datetime.now(UTC))

    def _apply_glicko2(
        self,
        model_a: str,
        model_b: str,
        score_a: float,
    ) -> None:
        """Apply Glicko-2 update for a single comparison between two models.

        Args:
            model_a: Winner's model name (or first model for ties)
            model_b: Loser's model name (or second model for ties)
            score_a: Score for model_a on [0, 1]. model_b gets 1 - score_a.
        """
        now = datetime.now(UTC)
        self.apply_rating_period([(model_a, model_b, score_a, 1.0)], now)
        self.session.commit()

    def apply_rating_period(
        self,
        games: list[tuple[str, str, float, float]],
        observed_at: datetime,
    ) -> None:
        """Apply all games simultaneously from the pre-period rating state."""
        if not games:
            return
        models = sorted({model for game in games for model in game[:2]})
        records = {model: self.get_or_create(model) for model in models}
        snapshots = {
            model: (record.elo_rating, record.rating_deviation, record.volatility, record.last_comparison_at)
            for model, record in records.items()
        }
        schedules: dict[str, list[tuple[str, float, float]]] = {model: [] for model in models}
        for model_a, model_b, score_a, weight in games:
            schedules[model_a].append((model_b, score_a, weight))
            schedules[model_b].append((model_a, 1.0 - score_a, weight))

        updates: dict[str, tuple[float, float, float]] = {}
        for model, schedule in schedules.items():
            rating, rd, volatility, last_observed = snapshots[model]
            updates[model] = _glicko2_update(
                rating,
                rd,
                volatility,
                [snapshots[opponent][0] for opponent, _, _ in schedule],
                [snapshots[opponent][1] for opponent, _, _ in schedule],
                [score for _, score, _ in schedule],
                [weight for _, _, weight in schedule],
                weeks_inactive=_weeks_between(last_observed, observed_at),
            )

        for model, (rating, rd, volatility) in updates.items():
            record = records[model]
            record.elo_rating = rating
            record.rating_deviation = rd
            record.volatility = volatility
            record.last_comparison_at = observed_at

        for model_a, model_b, score_a, _ in games:
            rec_a, rec_b = records[model_a], records[model_b]
            if score_a > 0.5:
                rec_a.wins += 1
                rec_b.losses += 1
            elif score_a < 0.5:
                rec_a.losses += 1
                rec_b.wins += 1
            else:
                rec_a.ties += 1
                rec_b.ties += 1

    def update_ratings(self, winner: str, loser: str, score: float = 1.0) -> tuple[float, float]:
        """Update ratings after a match. Returns (new_winner_rating, new_loser_rating)."""
        self._apply_glicko2(winner, loser, score)
        w_rec = self.get_or_create(winner)
        l_rec = self.get_or_create(loser)
        return w_rec.elo_rating, l_rec.elo_rating

    def record_tie(self, model_a: str, model_b: str) -> tuple[float, float]:
        """Record a tie between two models (score 0.5 each)."""
        self._apply_glicko2(model_a, model_b, 0.5)
        a_rec = self.get_or_create(model_a)
        b_rec = self.get_or_create(model_b)
        return a_rec.elo_rating, b_rec.elo_rating

    def record_comparison(
        self,
        query_id: int,
        user_id: int,
        winner_model: str | None,
        loser_model: str | None,
        translation_a_id: int | None = None,
        translation_b_id: int | None = None,
        source: str = "explicit",
        score: float | None = None,
    ) -> PairwiseComparison:
        """Record a pairwise comparison and update Glicko-2 ratings.

        Args:
            score: Game score for the winner on [0, 1]. If None, defaults to
                   1.0 for wins, 0.5 for ties. For derived comparisons, pass
                   the fractional score based on star rating gap.
        """
        if score is None:
            score = 0.5 if not winner_model else 1.0

        comparison = PairwiseComparison(
            query_id=query_id,
            user_id=user_id,
            winner_model=winner_model,
            loser_model=loser_model,
            translation_a_id=translation_a_id,
            translation_b_id=translation_b_id,
            source=source,
            score=score,
        )
        self.session.add(comparison)

        # Update ratings based on result
        if winner_model and loser_model:
            self._apply_glicko2(winner_model, loser_model, score)
        elif translation_a_id and translation_b_id and not winner_model:
            # Tie - get model names from translations
            t_a = self.session.get(Translation, translation_a_id)
            t_b = self.session.get(Translation, translation_b_id)
            if t_a and t_b:
                self._apply_glicko2(str(t_a.model), str(t_b.model), 0.5)

        return comparison

    def get_all_rankings(self) -> list[dict]:
        """Get all models ranked by Glicko-2 rating."""
        records = self.session.query(ModelELO).order_by(ModelELO.elo_rating.desc()).all()
        return [
            {
                "model": r.model,
                "elo_rating": r.elo_rating,
                "rating_deviation": r.rating_deviation or Config.GLICKO_INITIAL_RD,
                "volatility": r.volatility or Config.GLICKO_INITIAL_VOLATILITY,
                "wins": r.wins,
                "losses": r.losses,
                "ties": r.ties,
                "total_matches": r.total_matches,
                "win_rate": r.win_rate,
            }
            for r in records
        ]

    def rebuild_ratings_from_comparisons(self) -> int:
        """Deterministically project rating periods from raw comparisons."""
        from app.models import Translation as Trans

        seeds = {
            record.model: record.legacy_elo_rating
            for record in self.session.query(ModelELO).all()
            if record.legacy_elo_rating is not None
        }
        self.session.query(ModelELO).delete()
        self.session.flush()
        for model, seed in seeds.items():
            self.session.add(
                ModelELO(
                    model=model,
                    elo_rating=seed,
                    rating_deviation=Config.GLICKO_INITIAL_RD,
                    volatility=Config.GLICKO_INITIAL_VOLATILITY,
                    legacy_elo_rating=seed,
                )
            )
        self.session.flush()

        comparisons = (
            self.session.query(PairwiseComparison)
            .order_by(PairwiseComparison.created_at.asc(), PairwiseComparison.id.asc())
            .all()
        )

        # Pre-fetch all translations needed
        trans_ids = set()
        for c in comparisons:
            if c.translation_a_id:
                trans_ids.add(c.translation_a_id)
            if c.translation_b_id:
                trans_ids.add(c.translation_b_id)

        trans_map: dict[int, str] = {}
        if trans_ids:
            translations = self.session.query(Trans).filter(Trans.id.in_(trans_ids)).all()
            trans_map = {t.id: str(t.model) for t in translations}

        periods: dict[tuple[str, int], list[tuple[PairwiseComparison, str, str, float, float]]] = {}
        for c in comparisons:
            if c.winner_model and c.loser_model:
                model_a = c.winner_model
                model_b = c.loser_model
                score_a = c.score if c.score is not None else 1.0
            elif c.translation_a_id and c.translation_b_id:
                model_a = trans_map.get(c.translation_a_id)
                model_b = trans_map.get(c.translation_b_id)
                if not model_a or not model_b:
                    continue
                score_a = c.score if c.score is not None else 0.5
            else:
                continue
            if model_a == model_b:
                continue
            key = ("ballot", c.ballot_id) if c.source == "derived" and c.ballot_id else ("comparison", c.id)
            periods.setdefault(key, []).append((c, model_a, model_b, score_a, c.evidence_weight or 1.0))

        epoch = datetime(1970, 1, 1, tzinfo=UTC)

        def period_order(items):
            comparisons_in_period = [item[0] for item in items]
            ballot = comparisons_in_period[0].ballot
            observed_at = ballot.observed_at if ballot else comparisons_in_period[0].created_at
            return (_as_utc(observed_at) if observed_at else epoch, min(item.id for item in comparisons_in_period))

        count = 0
        for items in sorted(periods.values(), key=period_order):
            first = items[0][0]
            observed_at = first.ballot.observed_at if first.ballot else first.created_at
            observed_at = _as_utc(observed_at) if observed_at else epoch
            games = [(model_a, model_b, score, weight) for _, model_a, model_b, score, weight in items]
            self.apply_rating_period(games, observed_at)
            count += len(games)

        self.session.commit()
        logger.info("Rebuilt ratings from %d comparisons", count)
        return count

    def derive_from_existing_votes(self, user_id: int | None = None) -> int:
        """Derive pairwise comparisons from existing star rating votes.

        One-time migration function. Returns the number of comparisons derived.
        """
        from app.services.vote_service import _gap_to_score, _should_skip_pair

        vote_query = self.session.query(Vote)
        if user_id is not None:
            vote_query = vote_query.filter(Vote.user_id == user_id)
        votes = vote_query.all()

        translation_ids = {v.translation_id for v in votes if v.translation_id}
        translations = self.session.query(Translation).filter(Translation.id.in_(translation_ids)).all()
        translation_map = {t.id: t for t in translations}

        # Delete existing derived comparisons before re-deriving
        comp_query = self.session.query(PairwiseComparison).filter(PairwiseComparison.source == "derived")
        if user_id is not None:
            comp_query = comp_query.filter(PairwiseComparison.user_id == user_id)
        comp_query.delete()
        self.session.flush()

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

            for v1, v2 in combinations(group_votes, 2):
                if v1.rating is None or v2.rating is None:
                    continue

                t1 = translation_map.get(v1.translation_id)
                t2 = translation_map.get(v2.translation_id)
                if not t1 or not t2:
                    continue

                r1, r2 = v1.rating, v2.rating

                # Check tie logic
                if _should_skip_pair(r1, r2):
                    continue

                if r1 > r2:
                    winner_model = str(t1.model)
                    loser_model = str(t2.model)
                    score = _gap_to_score(abs(r1 - r2))
                elif r2 > r1:
                    winner_model = str(t2.model)
                    loser_model = str(t1.model)
                    score = _gap_to_score(abs(r1 - r2))
                else:
                    # Equal ratings: tie (0.5) for 1★ and 2★
                    winner_model = None
                    loser_model = None
                    score = 0.5

                self.record_comparison(
                    query_id=int(query_id),
                    user_id=int(uid),
                    winner_model=winner_model,
                    loser_model=loser_model,
                    translation_a_id=int(v1.translation_id) if v1.translation_id else None,
                    translation_b_id=int(v2.translation_id) if v2.translation_id else None,
                    source="derived",
                    score=score,
                )
                comparisons_created += 1

        logger.info("Derived %d pairwise comparisons from votes", comparisons_created)
        return comparisons_created


def get_elo_service(session: Session | None = None) -> ELOService:
    """Factory function to get ELO service instance."""
    return ELOService(session)
