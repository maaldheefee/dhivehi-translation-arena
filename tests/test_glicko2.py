"""Tests for Glicko-2 rating system, fractional scoring, and rebuild logic."""

import math

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from app.config import Config
from app.database import Base
from app.models import ModelELO, PairwiseComparison, Query, Translation, User, Vote
from app.services.elo_service import ELOService, _glicko2_update
from app.services.vote_service import _gap_to_score, _should_skip_pair


@pytest.fixture
def session():
    """Create an in-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine)
    session = scoped_session(SessionFactory)
    yield session
    session.remove()


@pytest.fixture
def elo_service(session):
    """Create an ELOService with the test session."""
    return ELOService(session)


# --- Glicko-2 algorithm tests ---


class TestGlicko2Update:
    """Tests for the core _glicko2_update function."""

    def test_no_games_only_rd_decay(self):
        """With no games, only RD time decay should apply."""
        rating, rd, vol = 1500.0, 200.0, 0.06
        new_r, new_rd, new_vol = _glicko2_update(rating, rd, vol, [], [], [], weeks_inactive=1.0)
        # Rating unchanged
        assert new_r == pytest.approx(1500.0, abs=0.01)
        # RD should increase due to time decay
        expected_rd = math.sqrt(200**2 + Config.GLICKO_C_PER_WEEK**2 * 1.0)
        assert new_rd == pytest.approx(expected_rd, abs=0.5)
        # Volatility unchanged
        assert new_vol == pytest.approx(0.06, abs=1e-6)

    def test_win_increases_rating(self):
        """A win should increase the winner's rating."""
        new_r, _, _ = _glicko2_update(
            1500.0,
            200.0,
            0.06,
            [1400.0],
            [30.0],
            [1.0],
        )
        assert new_r > 1500.0

    def test_loss_decreases_rating(self):
        """A loss should decrease the loser's rating."""
        new_r, _, _ = _glicko2_update(
            1500.0,
            200.0,
            0.06,
            [1400.0],
            [30.0],
            [0.0],
        )
        assert new_r < 1500.0

    def test_rd_decreases_after_game(self):
        """RD should decrease after a game (more certainty)."""
        _, new_rd, _ = _glicko2_update(
            1500.0,
            200.0,
            0.06,
            [1400.0],
            [30.0],
            [1.0],
        )
        assert new_rd < 200.0

    def test_min_rd_floor(self):
        """RD should not go below MIN_RD=80."""
        # Many games against low-RD opponent should push RD toward floor
        rating, rd, vol = 1500.0, 80.0, 0.06
        for _ in range(20):
            rating, rd, vol = _glicko2_update(
                rating,
                rd,
                vol,
                [1500.0],
                [80.0],
                [0.5],
            )
        assert rd >= Config.GLICKO_MIN_RD - 0.01

    def test_fractional_score(self):
        """A fractional score (0.7) should produce less rating change than 1.0."""
        new_r_win, _, _ = _glicko2_update(
            1500.0,
            200.0,
            0.06,
            [1500.0],
            [200.0],
            [1.0],
        )
        new_r_frac, _, _ = _glicko2_update(
            1500.0,
            200.0,
            0.06,
            [1500.0],
            [200.0],
            [0.7],
        )
        # Full win should move rating more than fractional win
        assert abs(new_r_win - 1500.0) > abs(new_r_frac - 1500.0)

    def test_tie_against_equal(self):
        """A tie (0.5) against equal opponent should barely change rating."""
        new_r, _, _ = _glicko2_update(
            1500.0,
            200.0,
            0.06,
            [1500.0],
            [200.0],
            [0.5],
        )
        assert new_r == pytest.approx(1500.0, abs=1.0)

    def test_upset_win_more_impact(self):
        """Winning against a higher-rated opponent should give more rating gain."""
        new_r_low, _, _ = _glicko2_update(
            1400.0,
            200.0,
            0.06,
            [1600.0],
            [200.0],
            [1.0],
        )
        new_r_high, _, _ = _glicko2_update(
            1600.0,
            200.0,
            0.06,
            [1400.0],
            [200.0],
            [1.0],
        )
        # Upset win (1400 beating 1600) should gain more than expected win
        assert (new_r_low - 1400.0) > (new_r_high - 1600.0)


# --- Fractional scoring tests ---


class TestGapToScore:
    """Tests for _gap_to_score function."""

    def test_gap_4_decisive(self):
        """3 vs -1 (gap=4) should give 1.0."""
        assert _gap_to_score(4) == 1.0

    def test_gap_3_strong(self):
        """2 vs -1 (gap=3) should give 0.95."""
        assert _gap_to_score(3) == 0.95

    def test_gap_2_clear(self):
        """3 vs 1 or 1 vs -1 (gap=2) should give 0.85."""
        assert _gap_to_score(2) == 0.85

    def test_gap_1_marginal(self):
        """3 vs 2 or 2 vs 1 (gap=1) should give 0.70."""
        assert _gap_to_score(1) == 0.70

    def test_gap_5_plus_decisive(self):
        """Gap >= 4 should always give 1.0."""
        assert _gap_to_score(5) == 1.0
        assert _gap_to_score(10) == 1.0


# --- Tie skip logic tests ---


class TestShouldSkipPair:
    """Tests for _should_skip_pair function with difficulty-aware logic."""

    def test_both_3_star_skipped_easy(self):
        """Both 3-star on easy query should be skipped."""
        assert _should_skip_pair(3, 3, "easy") is True

    def test_both_3_star_skipped_unknown(self):
        """Both 3-star on unknown query should be skipped (default behavior)."""
        assert _should_skip_pair(3, 3, "unknown") is True

    def test_both_3_star_skipped_default(self):
        """Both 3-star with no difficulty arg should be skipped (defaults to unknown)."""
        assert _should_skip_pair(3, 3) is True

    def test_both_3_star_tied_medium(self):
        """Both 3-star on medium query should NOT be skipped (tie)."""
        assert _should_skip_pair(3, 3, "medium") is False

    def test_both_3_star_tied_hard(self):
        """Both 3-star on hard query should NOT be skipped (tie)."""
        assert _should_skip_pair(3, 3, "hard") is False

    def test_both_neg1_star_skipped(self):
        """Both -1-star should be skipped regardless of difficulty."""
        assert _should_skip_pair(-1, -1, "easy") is True
        assert _should_skip_pair(-1, -1, "medium") is True
        assert _should_skip_pair(-1, -1, "hard") is True

    def test_both_1_star_not_skipped(self):
        """Both 1-star should NOT be skipped (tie)."""
        assert _should_skip_pair(1, 1) is False

    def test_both_2_star_not_skipped(self):
        """Both 2-star should NOT be skipped (tie)."""
        assert _should_skip_pair(2, 2) is False

    def test_unequal_not_skipped(self):
        """Unequal ratings should never be skipped."""
        assert _should_skip_pair(3, 2) is False
        assert _should_skip_pair(3, 1) is False
        assert _should_skip_pair(3, -1) is False
        assert _should_skip_pair(2, 1) is False
        assert _should_skip_pair(2, -1) is False
        assert _should_skip_pair(1, -1) is False


# --- ELOService integration tests ---


class TestELOService:
    """Tests for ELOService with database."""

    def test_get_or_create_default_values(self, elo_service, session):
        """New model should get default Glicko-2 values."""
        record = elo_service.get_or_create("test-model")
        assert record.elo_rating == Config.DEFAULT_RATING
        assert record.rating_deviation == Config.GLICKO_INITIAL_RD
        assert record.volatility == Config.GLICKO_INITIAL_VOLATILITY

    def test_update_ratings_win(self, elo_service, session):
        """Win should increase winner rating and decrease loser rating."""
        w_rating, l_rating = elo_service.update_ratings("winner", "loser")
        assert w_rating > Config.DEFAULT_RATING
        assert l_rating < Config.DEFAULT_RATING

    def test_record_tie(self, elo_service, session):
        """Tie should barely change ratings for equal models."""
        a_rating, b_rating = elo_service.record_tie("model-a", "model-b")
        # Equal models, tie should barely move
        assert abs(a_rating - Config.DEFAULT_RATING) < 20
        assert abs(b_rating - Config.DEFAULT_RATING) < 20

    def test_record_comparison_with_score(self, elo_service, session):
        """record_comparison should store the score in the comparison."""
        comp = elo_service.record_comparison(
            query_id=1,
            user_id=1,
            winner_model="winner",
            loser_model="loser",
            source="derived",
            score=0.85,
        )
        assert comp.score == 0.85
        # Check the comparison was persisted
        session.commit()
        stored = session.query(PairwiseComparison).first()
        assert stored is not None
        assert stored.score == 0.85

    def test_record_comparison_explicit_defaults_binary(self, elo_service, session):
        """Explicit comparison without score should default to 1.0."""
        comp = elo_service.record_comparison(
            query_id=1,
            user_id=1,
            winner_model="winner",
            loser_model="loser",
            source="explicit",
        )
        assert comp.score == 1.0

    def test_record_comparison_tie_defaults_half(self, elo_service, session):
        """Tie comparison without score should default to 0.5."""
        comp = elo_service.record_comparison(
            query_id=1,
            user_id=1,
            winner_model=None,
            loser_model=None,
            translation_a_id=1,
            translation_b_id=2,
            source="explicit",
        )
        assert comp.score == 0.5

    def test_win_loss_counters(self, elo_service, session):
        """Win/loss counters should be updated correctly."""
        elo_service.update_ratings("winner", "loser")
        w = elo_service.get_or_create("winner")
        loser = elo_service.get_or_create("loser")
        assert w.wins == 1
        assert loser.losses == 1

    def test_tie_counters(self, elo_service, session):
        """Tie counters should be updated correctly."""
        elo_service.record_tie("model-a", "model-b")
        a = elo_service.get_or_create("model-a")
        b = elo_service.get_or_create("model-b")
        assert a.ties == 1
        assert b.ties == 1

    def test_rd_decreases_after_comparison(self, elo_service, session):
        """RD should decrease after a comparison."""
        elo_service.update_ratings("model-a", "model-b")
        a = elo_service.get_or_create("model-a")
        assert a.rating_deviation < Config.GLICKO_INITIAL_RD

    def test_last_comparison_at_set(self, elo_service, session):
        """last_comparison_at should be set after a comparison."""
        elo_service.update_ratings("model-a", "model-b")
        a = elo_service.get_or_create("model-a")
        assert a.last_comparison_at is not None


# --- Rebuild tests ---


class TestRebuildRatings:
    """Tests for rebuild_ratings_from_comparisons."""

    def test_rebuild_matches_incremental(self, elo_service, session):
        """Rebuild should produce same ratings as incremental processing.

        Both paths apply time decay between consecutive comparisons for the
        same model. We use controlled timestamps to ensure identical decay.
        """
        from datetime import UTC, datetime, timedelta

        base_time = datetime(2025, 1, 1, tzinfo=UTC)

        comparisons_data = [
            ("model-a", "model-b", 1.0, base_time),
            ("model-a", "model-c", 0.85, base_time + timedelta(hours=1)),
            ("model-b", "model-c", 0.7, base_time + timedelta(hours=2)),
            ("model-c", "model-a", 1.0, base_time + timedelta(hours=3)),
            ("model-b", "model-a", 0.5, base_time + timedelta(hours=4)),
        ]

        # Insert comparisons with explicit timestamps
        for winner, loser, score, ts in comparisons_data:
            comp = PairwiseComparison(
                query_id=1,
                user_id=1,
                winner_model=winner,
                loser_model=loser,
                source="derived",
                score=score,
                created_at=ts,
            )
            session.add(comp)
        session.flush()

        # Rebuild from stored comparisons
        count = elo_service.rebuild_ratings_from_comparisons()
        assert count == len(comparisons_data)

        # Capture rebuilt ratings
        rebuilt_ratings = {}
        for model_name in ["model-a", "model-b", "model-c"]:
            rec = elo_service.get_or_create(model_name)
            rebuilt_ratings[model_name] = (
                rec.elo_rating,
                rec.rating_deviation,
                rec.volatility,
            )

        # Now simulate incremental processing with the same timestamps
        # Wipe and re-process one at a time, setting last_comparison_at to
        # match the comparison timestamp (as rebuild does)
        session.query(ModelELO).delete()
        session.flush()
        session.query(PairwiseComparison).delete()
        session.flush()

        # Re-insert comparisons
        for winner, loser, score, ts in comparisons_data:
            comp = PairwiseComparison(
                query_id=1,
                user_id=1,
                winner_model=winner,
                loser_model=loser,
                source="derived",
                score=score,
                created_at=ts,
            )
            session.add(comp)
        session.flush()

        # Manually replay with time decay (mimics incremental with known timestamps)
        for c in (
            session.query(PairwiseComparison)
            .order_by(PairwiseComparison.created_at.asc(), PairwiseComparison.id.asc())
            .all()
        ):
            rec_a = elo_service.get_or_create(c.winner_model)
            rec_b = elo_service.get_or_create(c.loser_model)

            comp_time = c.created_at
            if comp_time.tzinfo is None:
                comp_time = comp_time.replace(tzinfo=UTC)

            weeks_a = 0.0
            weeks_b = 0.0
            if rec_a.last_comparison_at is not None:
                last_a = rec_a.last_comparison_at
                if last_a.tzinfo is None:
                    last_a = last_a.replace(tzinfo=UTC)
                weeks_a = max(0.0, (comp_time - last_a).total_seconds() / (7 * 24 * 3600))
            if rec_b.last_comparison_at is not None:
                last_b = rec_b.last_comparison_at
                if last_b.tzinfo is None:
                    last_b = last_b.replace(tzinfo=UTC)
                weeks_b = max(0.0, (comp_time - last_b).total_seconds() / (7 * 24 * 3600))

            score = c.score if c.score is not None else 1.0
            new_r_a, new_rd_a, new_vol_a = _glicko2_update(
                rec_a.elo_rating,
                rec_a.rating_deviation,
                rec_a.volatility,
                [rec_b.elo_rating],
                [rec_b.rating_deviation],
                [score],
                weeks_inactive=weeks_a,
            )
            new_r_b, new_rd_b, new_vol_b = _glicko2_update(
                rec_b.elo_rating,
                rec_b.rating_deviation,
                rec_b.volatility,
                [rec_a.elo_rating],
                [rec_a.rating_deviation],
                [1.0 - score],
                weeks_inactive=weeks_b,
            )
            rec_a.elo_rating = new_r_a
            rec_a.rating_deviation = new_rd_a
            rec_a.volatility = new_vol_a
            rec_a.last_comparison_at = comp_time
            rec_b.elo_rating = new_r_b
            rec_b.rating_deviation = new_rd_b
            rec_b.volatility = new_vol_b
            rec_b.last_comparison_at = comp_time

        # Compare rebuilt vs manually-replayed (should be identical)
        for model_name in ["model-a", "model-b", "model-c"]:
            rec = elo_service.get_or_create(model_name)
            rb_r, rb_rd, rb_vol = rebuilt_ratings[model_name]
            assert rec.elo_rating == pytest.approx(rb_r, abs=0.01), (
                f"{model_name}: replay {rec.elo_rating} vs rebuild {rb_r}"
            )
            assert rec.rating_deviation == pytest.approx(rb_rd, abs=0.01), (
                f"{model_name}: replay RD {rec.rating_deviation} vs rebuild RD {rb_rd}"
            )
            assert rec.volatility == pytest.approx(rb_vol, abs=1e-6), (
                f"{model_name}: replay vol {rec.volatility} vs rebuild vol {rb_vol}"
            )

    def test_rebuild_idempotent(self, elo_service, session):
        """Running rebuild twice should produce the same results."""
        # Add some comparisons
        for _ in range(5):
            elo_service.record_comparison(
                query_id=1,
                user_id=1,
                winner_model="model-a",
                loser_model="model-b",
                source="derived",
                score=0.85,
            )

        # First rebuild
        elo_service.rebuild_ratings_from_comparisons()
        first_ratings = {}
        for model_name in ["model-a", "model-b"]:
            rec = elo_service.get_or_create(model_name)
            first_ratings[model_name] = (rec.elo_rating, rec.rating_deviation)

        # Second rebuild
        elo_service.rebuild_ratings_from_comparisons()
        for model_name in ["model-a", "model-b"]:
            rec = elo_service.get_or_create(model_name)
            assert rec.elo_rating == pytest.approx(first_ratings[model_name][0], abs=0.01)
            assert rec.rating_deviation == pytest.approx(first_ratings[model_name][1], abs=0.01)

    def test_rebuild_stable_order(self, elo_service, session):
        """Rebuild should process comparisons in created_at asc, id asc order."""
        # Create comparisons with different timestamps
        from datetime import UTC, datetime, timedelta

        base_time = datetime(2025, 1, 1, tzinfo=UTC)

        for i in range(3):
            comp = PairwiseComparison(
                query_id=1,
                user_id=1,
                winner_model="model-a",
                loser_model="model-b",
                source="derived",
                score=1.0,
                created_at=base_time + timedelta(hours=i),
            )
            session.add(comp)
        session.commit()

        elo_service.rebuild_ratings_from_comparisons()

        a = elo_service.get_or_create("model-a")
        b = elo_service.get_or_create("model-b")
        # model-a won all 3, should be higher
        assert a.elo_rating > b.elo_rating
        assert a.wins == 3
        assert b.losses == 3


# --- Vote service integration tests ---


class TestVoteDerivation:
    """Tests for vote-to-comparison derivation with fractional scoring."""

    def _create_test_data(self, session):
        """Helper to create user, query, and two translations."""
        user = User(username="testuser", password_hash="x")
        session.add(user)
        session.flush()

        query = Query(source_text="test")
        session.add(query)
        session.flush()

        t1 = Translation(
            query_id=query.id,
            model="model-a",
            translation="A",
            system_prompt="sp",
            position=1,
            user_id=user.id,
        )
        t2 = Translation(
            query_id=query.id,
            model="model-b",
            translation="B",
            system_prompt="sp",
            position=2,
            user_id=user.id,
        )
        session.add_all([t1, t2])
        session.flush()
        return user, query, t1, t2

    def test_fractional_score_stored(self, elo_service, session):
        """Derived comparisons should store fractional scores based on gap."""
        user, query, t1, t2 = self._create_test_data(session)

        # 3 vs 1 -> gap=2 -> score=0.85
        from app.services.vote_service import _derive_pairwise_from_votes

        votes_data = [
            {"translation_id": t1.id, "rating": 3},
            {"translation_id": t2.id, "rating": 1},
        ]
        _derive_pairwise_from_votes(session, int(user.id), int(query.id), votes_data)
        session.commit()

        comp = session.query(PairwiseComparison).filter(PairwiseComparison.source == "derived").first()
        assert comp is not None
        assert comp.score == 0.85

    def test_both_3_star_skipped(self, session):
        """Both 3-star should not produce a comparison."""
        user, query, t1, t2 = self._create_test_data(session)

        from app.services.vote_service import _derive_pairwise_from_votes

        votes_data = [
            {"translation_id": t1.id, "rating": 3},
            {"translation_id": t2.id, "rating": 3},
        ]
        _derive_pairwise_from_votes(session, int(user.id), int(query.id), votes_data)
        session.commit()

        count = session.query(PairwiseComparison).filter(PairwiseComparison.source == "derived").count()
        assert count == 0

    def test_both_neg1_star_skipped(self, session):
        """Both -1-star should not produce a comparison."""
        user, query, t1, t2 = self._create_test_data(session)

        from app.services.vote_service import _derive_pairwise_from_votes

        votes_data = [
            {"translation_id": t1.id, "rating": -1},
            {"translation_id": t2.id, "rating": -1},
        ]
        _derive_pairwise_from_votes(session, int(user.id), int(query.id), votes_data)
        session.commit()

        count = session.query(PairwiseComparison).filter(PairwiseComparison.source == "derived").count()
        assert count == 0

    def test_equal_1_star_tie(self, session):
        """Both 1-star should produce a tie (score=0.5)."""
        user, query, t1, t2 = self._create_test_data(session)

        from app.services.vote_service import _derive_pairwise_from_votes

        votes_data = [
            {"translation_id": t1.id, "rating": 1},
            {"translation_id": t2.id, "rating": 1},
        ]
        _derive_pairwise_from_votes(session, int(user.id), int(query.id), votes_data)
        session.commit()

        comp = session.query(PairwiseComparison).filter(PairwiseComparison.source == "derived").first()
        assert comp is not None
        assert comp.winner_model is None
        assert comp.loser_model is None
        assert comp.score == 0.5

    def test_delete_before_rederive(self, session):
        """Re-voting should delete old derived comparisons before re-deriving."""
        user, query, t1, t2 = self._create_test_data(session)

        from app.services.vote_service import _derive_pairwise_from_votes

        # First vote: 3 vs 1
        votes_data = [
            {"translation_id": t1.id, "rating": 3},
            {"translation_id": t2.id, "rating": 1},
        ]
        _derive_pairwise_from_votes(session, int(user.id), int(query.id), votes_data)
        session.commit()

        initial_count = (
            session.query(PairwiseComparison)
            .filter(
                PairwiseComparison.source == "derived",
                PairwiseComparison.query_id == query.id,
            )
            .count()
        )
        assert initial_count == 1

        # Re-vote: 1 vs 3 (reversed)
        votes_data = [
            {"translation_id": t1.id, "rating": 1},
            {"translation_id": t2.id, "rating": 3},
        ]
        _derive_pairwise_from_votes(session, int(user.id), int(query.id), votes_data)
        session.commit()

        # Should still have only 1 comparison (old one deleted, new one created)
        comps = (
            session.query(PairwiseComparison)
            .filter(
                PairwiseComparison.source == "derived",
                PairwiseComparison.query_id == query.id,
            )
            .all()
        )
        assert len(comps) == 1
        # Winner should now be model-b
        assert comps[0].winner_model == "model-b"

    def test_revote_rebuilds_ratings(self, elo_service, session):
        """Re-voting must rebuild ratings to match stored comparisons."""
        user, query, t1, t2 = self._create_test_data(session)

        from app.services.vote_service import _derive_pairwise_from_votes

        # First vote: 3 vs 1 -> model-a wins with score 0.85
        votes_data = [
            {"translation_id": t1.id, "rating": 3},
            {"translation_id": t2.id, "rating": 1},
        ]
        _derive_pairwise_from_votes(session, int(user.id), int(query.id), votes_data)
        session.commit()

        # Re-vote: 1 vs 3 -> model-b wins with score 0.85 (reversed)
        votes_data = [
            {"translation_id": t1.id, "rating": 1},
            {"translation_id": t2.id, "rating": 3},
        ]
        _derive_pairwise_from_votes(session, int(user.id), int(query.id), votes_data)
        session.commit()

        # Ratings should now reflect model-b winning, not stacked on top of old
        rec_a = elo_service.get_or_create("model-a")
        rec_b = elo_service.get_or_create("model-b")

        # model-a should now be below default (it lost)
        assert rec_a.elo_rating < Config.DEFAULT_RATING
        # model-b should now be above default (it won)
        assert rec_b.elo_rating > Config.DEFAULT_RATING

        # Verify by doing a fresh rebuild — ratings should match
        elo_service.rebuild_ratings_from_comparisons()
        rec_a_rebuild = elo_service.get_or_create("model-a")
        rec_b_rebuild = elo_service.get_or_create("model-b")
        assert rec_a.elo_rating == pytest.approx(rec_a_rebuild.elo_rating, abs=0.01)
        assert rec_b.elo_rating == pytest.approx(rec_b_rebuild.elo_rating, abs=0.01)

    def test_partial_vote_preserves_all_comparisons(self, session):
        """Partial vote submission must re-derive from ALL persisted votes.

        Simulates what process_votes does: after upserting a partial vote set,
        fetch ALL persisted votes for the user+query and pass them to
        _derive_pairwise_from_votes.
        """
        user = User(username="testuser", password_hash="x")
        session.add(user)
        session.flush()

        query = Query(source_text="test")
        session.add(query)
        session.flush()

        # Create 3 translations for 3 models
        translations = []
        for i, model in enumerate(["model-a", "model-b", "model-c"]):
            t = Translation(
                query_id=query.id,
                model=model,
                translation=f"T{i}",
                system_prompt="sp",
                position=i + 1,
                user_id=user.id,
            )
            session.add(t)
            translations.append(t)
        session.flush()

        t1, t2, t3 = translations

        # Persist initial votes: 3, 1, 2
        for tid, rating in [(t1.id, 3), (t2.id, 1), (t3.id, 2)]:
            vote = Vote(
                user_id=user.id,
                query_id=query.id,
                translation_id=tid,
                rating=rating,
            )
            session.add(vote)
        session.flush()

        # Derive from all persisted votes (as process_votes does)
        from app.services.vote_service import _derive_pairwise_from_votes

        persisted = session.query(Vote).filter(Vote.user_id == user.id, Vote.query_id == query.id).all()
        all_votes_data = [
            {"translation_id": v.translation_id, "rating": v.rating} for v in persisted if v.rating is not None
        ]
        _derive_pairwise_from_votes(session, int(user.id), int(query.id), all_votes_data)
        session.commit()

        initial_count = (
            session.query(PairwiseComparison)
            .filter(
                PairwiseComparison.source == "derived",
                PairwiseComparison.query_id == query.id,
            )
            .count()
        )
        assert initial_count == 3  # C(3,2) = 3 pairs

        # Simulate partial update: change t1 and t2 ratings in persisted votes
        for v in session.query(Vote).filter(Vote.query_id == query.id, Vote.user_id == user.id).all():
            if v.translation_id == t1.id:
                v.rating = 1
            elif v.translation_id == t2.id:
                v.rating = 3
        session.flush()

        # Fetch ALL persisted votes (as process_votes does after the fix)
        persisted_votes = session.query(Vote).filter(Vote.user_id == user.id, Vote.query_id == query.id).all()
        all_votes_data = [
            {"translation_id": v.translation_id, "rating": v.rating} for v in persisted_votes if v.rating is not None
        ]
        _derive_pairwise_from_votes(session, int(user.id), int(query.id), all_votes_data)
        session.commit()

        # Should still have 3 comparisons (all 3 persisted votes considered)
        final_count = (
            session.query(PairwiseComparison)
            .filter(
                PairwiseComparison.source == "derived",
                PairwiseComparison.query_id == query.id,
            )
            .count()
        )
        assert final_count == 3


# --- Pair priority tests ---


class TestPairPriority:
    """Tests for _compute_pair_priority composite scoring."""

    def test_close_elo_higher_priority(self):
        """Closer ELO should yield higher elo_closeness component."""
        from app.blueprints.main import _compute_pair_priority

        close = _compute_pair_priority(1500, 200, 1510, 200, 0, False)
        far = _compute_pair_priority(1500, 200, 1600, 200, 0, False)
        assert close > far

    def test_high_rd_higher_uncertainty(self):
        """Higher RD should yield higher uncertainty component."""
        from app.blueprints.main import _compute_pair_priority

        high_rd = _compute_pair_priority(1500, 300, 1500, 300, 0, False)
        low_rd = _compute_pair_priority(1500, 80, 1500, 80, 0, False)
        assert high_rd > low_rd

    def test_hungry_pair_higher_priority(self):
        """Fewer comparisons should yield higher pair_hunger."""
        from app.blueprints.main import _compute_pair_priority

        hungry = _compute_pair_priority(1500, 200, 1500, 200, 0, False)
        sated = _compute_pair_priority(1500, 200, 1500, 200, 10, False)
        assert hungry > sated

    def test_same_rating_bonus(self):
        """Same-rated pairs should get +0.3 bonus."""
        from app.blueprints.main import _compute_pair_priority

        same = _compute_pair_priority(1500, 200, 1500, 200, 0, True)
        diff = _compute_pair_priority(1500, 200, 1500, 200, 0, False)
        assert same - diff == pytest.approx(0.3, abs=0.001)

    def test_weights_sum_correctly(self):
        """Composite score should be sum of weighted components + bonus."""
        from app.blueprints.main import _compute_pair_priority

        elo_a, rd_a, elo_b, rd_b = 1500, 200, 1500, 200
        score = _compute_pair_priority(elo_a, rd_a, elo_b, rd_b, 5, True)
        # Manually compute
        elo_closeness = 1.0 / (1.0 + abs(elo_a - elo_b) / 100.0)  # 1.0
        uncertainty = min(1.0, 200 / 350.0)  # ~0.571
        pair_hunger = 1.0 / 6.0  # ~0.167
        expected = elo_closeness * 0.30 + uncertainty * 0.25 + pair_hunger * 0.25 + 0.3
        assert score == pytest.approx(expected, abs=0.001)


# --- Difficulty-aware tie tests ---


class TestDifficultyAwareTie:
    """Tests for 3★/3★ tie behavior with query difficulty."""

    def _create_test_data(self, session):
        """Helper to create user, query, and two translations."""
        user = User(username="testuser", password_hash="x")
        session.add(user)
        session.flush()
        query = Query(source_text="test")
        session.add(query)
        session.flush()
        t1 = Translation(
            query_id=query.id,
            model="model-a",
            translation="A",
            system_prompt="sp",
            position=1,
            user_id=user.id,
        )
        t2 = Translation(
            query_id=query.id,
            model="model-b",
            translation="B",
            system_prompt="sp",
            position=2,
            user_id=user.id,
        )
        session.add_all([t1, t2])
        session.flush()
        return user, query, t1, t2

    def test_3_star_tied_on_hard_query(self, session):
        """Both 3-star on a hard query should produce a tie (not skipped)."""
        from app.services.vote_service import _derive_pairwise_from_votes

        user, query, t1, t2 = self._create_test_data(session)
        votes_data = [
            {"translation_id": t1.id, "rating": 3},
            {"translation_id": t2.id, "rating": 3},
        ]
        _derive_pairwise_from_votes(session, int(user.id), int(query.id), votes_data, "hard")
        session.commit()

        comp = session.query(PairwiseComparison).filter(PairwiseComparison.source == "derived").first()
        assert comp is not None
        assert comp.winner_model is None
        assert comp.score == 0.5

    def test_3_star_skipped_on_easy_query(self, session):
        """Both 3-star on an easy query should be skipped (no comparison)."""
        from app.services.vote_service import _derive_pairwise_from_votes

        user, query, t1, t2 = self._create_test_data(session)
        votes_data = [
            {"translation_id": t1.id, "rating": 3},
            {"translation_id": t2.id, "rating": 3},
        ]
        _derive_pairwise_from_votes(session, int(user.id), int(query.id), votes_data, "easy")
        session.commit()

        count = session.query(PairwiseComparison).filter(PairwiseComparison.source == "derived").count()
        assert count == 0


# --- Confidence-weighted leaderboard tests ---


class TestConfidenceWeightedBlend:
    """Tests for RD-aware confidence weighting in calculate_model_scores."""

    def test_high_confidence_glicko_dominates(self, session):
        """With low RD (high confidence), Glicko-2 should dominate the blend."""
        from unittest.mock import patch

        from app.services.stats_service import calculate_model_scores

        # Create model with low RD (confident)
        elo = ModelELO(model="confident-model", elo_rating=1800, rating_deviation=80)
        session.add(elo)

        # Create translation and vote with mediocre star rating
        user = User(username="testuser", password_hash="x")
        session.add(user)
        session.flush()
        query = Query(source_text="test")
        session.add(query)
        session.flush()
        t = Translation(
            query_id=query.id,
            model="confident-model",
            translation="A",
            system_prompt="sp",
            position=1,
            user_id=user.id,
        )
        session.add(t)
        session.flush()
        vote = Vote(user_id=user.id, query_id=query.id, translation_id=t.id, rating=1)
        session.add(vote)
        session.commit()

        with patch("app.services.stats_service.db_session", session):
            scores = calculate_model_scores()
        model_score = next(s for s in scores if s["model_name"] == "confident-model")

        # Score mapping: rating=1 -> score=0, so average_score=0
        # normalized_avg = (0+2)/5 = 0.4
        # With RD=80, confidence = 1 - 80/350 ≈ 0.77
        # normalized_elo = (1800-1000)/1000 = 0.8
        # combined ≈ 0.8*0.77 + 0.4*0.23 ≈ 0.709
        assert model_score["combined_score"] > 0.65
        assert model_score["rating_deviation"] == 80

    def test_low_confidence_stars_dominate(self, session):
        """With high RD (low confidence), star ratings should dominate."""
        from unittest.mock import patch

        from app.services.stats_service import calculate_model_scores

        # Create model with high RD (uncertain)
        elo = ModelELO(model="uncertain-model", elo_rating=1800, rating_deviation=340)
        session.add(elo)

        user = User(username="testuser2", password_hash="x")
        session.add(user)
        session.flush()
        query = Query(source_text="test2")
        session.add(query)
        session.flush()
        t = Translation(
            query_id=query.id,
            model="uncertain-model",
            translation="A",
            system_prompt="sp",
            position=1,
            user_id=user.id,
        )
        session.add(t)
        session.flush()
        vote = Vote(user_id=user.id, query_id=query.id, translation_id=t.id, rating=1)
        session.add(vote)
        session.commit()

        with patch("app.services.stats_service.db_session", session):
            scores = calculate_model_scores()
        model_score = next(s for s in scores if s["model_name"] == "uncertain-model")

        # Score mapping: rating=1 -> score=0, so average_score=0
        # normalized_avg = (0+2)/5 = 0.4
        # With RD=340, confidence = 1 - 340/350 ≈ 0.029
        # normalized_elo = 0.8, normalized_avg = 0.4
        # combined ≈ 0.8*0.03 + 0.4*0.97 ≈ 0.411
        # Star rating should dominate over Glicko
        assert model_score["combined_score"] < 0.5
        assert model_score["combined_score"] > 0.35

    def test_weights_sum_to_one(self, session):
        """Confidence + (1 - confidence) should always equal 1.0."""
        from unittest.mock import patch

        from app.services.stats_service import calculate_model_scores

        for rd in [80, 150, 250, 350]:
            model_name = f"rd-test-{rd}"
            elo = ModelELO(model=model_name, elo_rating=1500, rating_deviation=rd)
            session.add(elo)

            user = User(username=f"user-{rd}", password_hash="x")
            session.add(user)
            session.flush()
            query = Query(source_text=f"q-{rd}")
            session.add(query)
            session.flush()
            t = Translation(
                query_id=query.id,
                model=model_name,
                translation="A",
                system_prompt="sp",
                position=1,
                user_id=user.id,
            )
            session.add(t)
            session.flush()
            vote = Vote(user_id=user.id, query_id=query.id, translation_id=t.id, rating=2)
            session.add(vote)
        session.commit()

        with patch("app.services.stats_service.db_session", session):
            scores = calculate_model_scores()
        for rd in [80, 150, 250, 350]:
            model_name = f"rd-test-{rd}"
            ms = next(s for s in scores if s["model_name"] == model_name)
            confidence = 1.0 - (rd / 350.0)
            # Score mapping: rating=2 -> score=1, so average_score=1.0
            # normalized_avg = (1+2)/5 = 0.6
            # normalized_elo = (1500-1000)/1000 = 0.5
            normalized_elo = max(0.0, min(1.0, (1500 - 1000) / 1000))
            normalized_avg = max(0.0, min(1.0, (1.0 + 2) / 5))
            expected = normalized_elo * confidence + normalized_avg * (1 - confidence)
            assert ms["combined_score"] == pytest.approx(expected, abs=0.01), (
                f"RD={rd}: expected {expected}, got {ms['combined_score']}"
            )


# --- Cost-aware model selection tests ---


class TestCostAwareModelSelection:
    """Tests for max expensive groups constraint in _select_models."""

    def test_max_two_expensive_groups(self):
        """Should limit to MAX_EXPENSIVE_GROUPS expensive base model groups."""
        from app.blueprints.main import _select_models
        from app.config import Config

        # Create config with 3 expensive base model groups, each with 1 model
        config = Config()
        # Override models dict for testing
        config.MODELS = {  # ty: ignore[invalid-attribute-access]
            "cheap-1": {
                "base_model": "cheap-a",
                "output_cost_per_mtok": 1.0,
                "is_active": True,
            },
            "cheap-2": {
                "base_model": "cheap-b",
                "output_cost_per_mtok": 2.0,
                "is_active": True,
            },
            "exp-1": {
                "base_model": "exp-a",
                "output_cost_per_mtok": 15.0,
                "is_active": True,
            },
            "exp-2": {
                "base_model": "exp-b",
                "output_cost_per_mtok": 20.0,
                "is_active": True,
            },
            "exp-3": {
                "base_model": "exp-c",
                "output_cost_per_mtok": 25.0,
                "is_active": True,
            },
        }

        available = {k: v["base_model"] for k, v in config.MODELS.items() if v["base_model"]}
        usage_stats = dict.fromkeys(config.MODELS, 0)

        selected = _select_models(available, usage_stats, config, max_models=5)

        # Count expensive groups in selection
        expensive_bases = set()
        for key in selected:
            base = config.MODELS[key]["base_model"]
            cost = config.MODELS[key]["output_cost_per_mtok"]
            if cost > config.COST_MID_MAX:
                expensive_bases.add(base)

        assert len(expensive_bases) <= config.MAX_EXPENSIVE_GROUPS

    def test_cheap_models_not_constrained(self):
        """Cheap and mid-cost models should not be affected by the constraint."""
        from app.blueprints.main import _select_models
        from app.config import Config

        config = Config()
        config.MODELS = {  # ty: ignore[invalid-attribute-access]
            "cheap-1": {
                "base_model": "cheap-a",
                "output_cost_per_mtok": 1.0,
                "is_active": True,
            },
            "cheap-2": {
                "base_model": "cheap-b",
                "output_cost_per_mtok": 2.0,
                "is_active": True,
            },
            "mid-1": {
                "base_model": "mid-a",
                "output_cost_per_mtok": 5.0,
                "is_active": True,
            },
            "mid-2": {
                "base_model": "mid-b",
                "output_cost_per_mtok": 8.0,
                "is_active": True,
            },
        }

        available = {k: v["base_model"] for k, v in config.MODELS.items() if v["base_model"]}
        usage_stats = dict.fromkeys(config.MODELS, 0)

        selected = _select_models(available, usage_stats, config, max_models=4)
        assert len(selected) == 4  # All should be selected, no expensive models

    def test_backfill_excludes_expensive_models(self):
        """Backfill after removing expensive groups must not re-add expensive models."""
        from app.blueprints.main import _select_models
        from app.config import Config

        config = Config()
        config.MODELS = {  # ty: ignore[invalid-attribute-access]
            "cheap-1": {
                "base_model": "cheap-a",
                "output_cost_per_mtok": 1.0,
                "is_active": True,
            },
            "exp-1": {
                "base_model": "exp-a",
                "output_cost_per_mtok": 15.0,
                "is_active": True,
            },
            "exp-2": {
                "base_model": "exp-b",
                "output_cost_per_mtok": 20.0,
                "is_active": True,
            },
            "exp-3": {
                "base_model": "exp-c",
                "output_cost_per_mtok": 25.0,
                "is_active": True,
            },
        }

        available = {k: v["base_model"] for k, v in config.MODELS.items() if v["base_model"]}
        # Give cheap-1 high usage so it's selected last
        usage_stats = {"cheap-1": 100, "exp-1": 0, "exp-2": 0, "exp-3": 0}

        selected = _select_models(available, usage_stats, config, max_models=3)

        # Count expensive groups in result
        expensive_bases = set()
        for key in selected:
            base = config.MODELS[key]["base_model"]
            cost = config.MODELS[key]["output_cost_per_mtok"]
            if cost > config.COST_MID_MAX:
                expensive_bases.add(base)

        assert len(expensive_bases) <= config.MAX_EXPENSIVE_GROUPS
        # cheap-1 must be in the result (backfilled from cheap pool)
        assert "cheap-1" in selected


# --- Query difficulty classification tests ---


class TestQueryDifficulty:
    """Tests for difficulty tier classification correctness."""

    def test_high_residuals_classified_easy(self, session):
        """Models beating their baseline → easy query."""
        from unittest.mock import patch

        from app.services.stats_service import get_query_difficulty, invalidate_caches

        invalidate_caches()

        # Create 3 models with low global averages (usually get 1-star)
        for model_name in ["weak-a", "weak-b", "weak-c"]:
            elo = ModelELO(model=model_name, elo_rating=1500, rating_deviation=350)
            session.add(elo)

        user = User(username="diff-test-user", password_hash="x")
        session.add(user)
        session.flush()

        # Baseline query: models get 1-star (sets low global average)
        baseline = Query(source_text="baseline-easy")
        session.add(baseline)
        session.flush()
        for i, model in enumerate(["weak-a", "weak-b", "weak-c"]):
            t = Translation(
                query_id=baseline.id,
                model=model,
                translation="T",
                system_prompt="sp",
                position=i + 1,
                user_id=user.id,
            )
            session.add(t)
        session.flush()
        for t in session.query(Translation).filter(Translation.query_id == baseline.id).all():
            vote = Vote(user_id=user.id, query_id=baseline.id, translation_id=t.id, rating=1)
            session.add(vote)

        # Test query: same models get 3-star (above baseline → positive residual)
        query = Query(source_text="easy-query")
        session.add(query)
        session.flush()
        for i, model in enumerate(["weak-a", "weak-b", "weak-c"]):
            t = Translation(
                query_id=query.id,
                model=model,
                translation="T",
                system_prompt="sp",
                position=i + 1,
                user_id=user.id,
            )
            session.add(t)
        session.flush()
        for t in session.query(Translation).filter(Translation.query_id == query.id).all():
            vote = Vote(user_id=user.id, query_id=query.id, translation_id=t.id, rating=3)
            session.add(vote)
        session.commit()

        with patch("app.services.stats_service.db_session", session):
            difficulty = get_query_difficulty()

        # residual = 3 - 1 = 2.0, well above EASY_THRESHOLD (0.3)
        assert difficulty.get(int(query.id)) == "easy"

    def test_low_residuals_classified_hard(self, session):
        """Models underperforming their baseline → hard query."""
        from unittest.mock import patch

        from app.services.stats_service import get_query_difficulty, invalidate_caches

        invalidate_caches()

        # Create 3 models with high global averages (usually get 3-star)
        for model_name in ["strong-a", "strong-b", "strong-c"]:
            elo = ModelELO(model=model_name, elo_rating=1500, rating_deviation=350)
            session.add(elo)

        user = User(username="diff-test-user2", password_hash="x")
        session.add(user)
        session.flush()

        # Baseline query: models get 3-star (sets high global average)
        baseline = Query(source_text="baseline-hard")
        session.add(baseline)
        session.flush()
        for i, model in enumerate(["strong-a", "strong-b", "strong-c"]):
            t = Translation(
                query_id=baseline.id,
                model=model,
                translation="T",
                system_prompt="sp",
                position=i + 1,
                user_id=user.id,
            )
            session.add(t)
        session.flush()
        for t in session.query(Translation).filter(Translation.query_id == baseline.id).all():
            vote = Vote(user_id=user.id, query_id=baseline.id, translation_id=t.id, rating=3)
            session.add(vote)

        # Test query: same models get -1 (below baseline → negative residual)
        query = Query(source_text="hard-query")
        session.add(query)
        session.flush()
        for i, model in enumerate(["strong-a", "strong-b", "strong-c"]):
            t = Translation(
                query_id=query.id,
                model=model,
                translation="T",
                system_prompt="sp",
                position=i + 1,
                user_id=user.id,
            )
            session.add(t)
        session.flush()
        for t in session.query(Translation).filter(Translation.query_id == query.id).all():
            vote = Vote(user_id=user.id, query_id=query.id, translation_id=t.id, rating=-1)
            session.add(vote)
        session.commit()

        with patch("app.services.stats_service.db_session", session):
            difficulty = get_query_difficulty()

        # residual = -1 - 3 = -4.0, well below HARD_THRESHOLD (-0.3)
        assert difficulty.get(int(query.id)) == "hard"


class TestPairComparisonCounts:
    """Tests for get_pair_comparison_counts — regression test for SQLite
    ambiguous column name error when using string labels in group_by."""

    def test_pair_counts_with_explicit_comparisons(self, session):
        """Verify pair counts are computed correctly without SQL errors."""
        from unittest.mock import patch

        from app.services.stats_service import get_pair_comparison_counts

        user = User(username="testuser", password_hash="x")
        session.add(user)
        session.flush()

        query = Query(source_text="test")
        session.add(query)
        session.flush()

        t1 = Translation(
            query_id=query.id,
            model="model-a",
            translation="A",
            system_prompt="sp",
            position=1,
            user_id=user.id,
        )
        t2 = Translation(
            query_id=query.id,
            model="model-b",
            translation="B",
            system_prompt="sp",
            position=2,
            user_id=user.id,
        )
        session.add_all([t1, t2])
        session.flush()

        # Add explicit comparison
        comp = PairwiseComparison(
            user_id=user.id,
            query_id=query.id,
            translation_a_id=t1.id,
            translation_b_id=t2.id,
            winner_model="model-a",
            loser_model="model-b",
            source="explicit",
            score=1.0,
        )
        session.add(comp)
        session.commit()

        with patch("app.services.stats_service.db_session", session):
            counts = get_pair_comparison_counts()

        key = ("model-a", "model-b")
        assert key in counts
        assert counts[key] == 1
