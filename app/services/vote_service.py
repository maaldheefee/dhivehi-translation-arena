"""Vote service for processing hybrid voting system votes."""

import logging
from datetime import UTC, datetime
from hashlib import sha256
from itertools import combinations
from typing import cast

from sqlalchemy.orm import Session

from app.database import db_session
from app.models import PairwiseComparison, RatingBallot, Translation, Vote
from app.repositories.vote_repository import VoteRepository
from app.services.elo_service import get_elo_service
from app.services.stats_service import invalidate_caches

logger = logging.getLogger(__name__)


def _gap_to_score(gap: int) -> float:
    """Map star rating gap to a fractional Glicko-2 score.

    Rating scale: 3, 2, 1, -1 (NOT 3, 2, 1, 0)
    gap=4 -> 1.0  (3 vs -1, decisive)
    gap=3 -> 0.95 (2 vs -1, strong)
    gap=2 -> 0.85 (3 vs 1, or 1 vs -1, clear)
    gap=1 -> 0.70 (3 vs 2, or 2 vs 1, marginal)
    """
    if gap >= 4:
        return 1.0
    elif gap >= 3:
        return 0.95
    elif gap >= 2:
        return 0.85
    else:
        return 0.70


def _should_skip_pair(r1: int, r2: int, query_difficulty: str = "unknown") -> bool:
    """Determine if a pair of ratings should be skipped (no comparison recorded).

    Skip rules:
    - Both 3-star on easy/unknown queries: perfection on trivial query, not comparative skill
    - Both 3-star on medium/hard queries: tie (both models nailed a challenging translation)
    - Both -1-star: both trash, no meaningful comparison
    """
    if r1 == 3 and r2 == 3:
        # On easy or unknown queries, skip 3★/3★ (perfection signal, not skill)
        # On medium/hard queries, record as tie (both models succeeded on something hard)
        return query_difficulty in ("easy", "unknown")
    return bool(r1 == -1 and r2 == -1)


def _canonical_votes(votes_data) -> list[tuple[int, int]]:
    """Validate and canonicalize one ballot payload."""
    ratings: dict[int, int] = {}
    for item in votes_data:
        translation_id = item.get("translation_id")
        rating = item.get("rating")
        if not isinstance(translation_id, int) or rating not in (3, 2, 1, -1):
            raise ValueError("Every ballot item must contain a translation ID and valid rating")
        if translation_id in ratings and ratings[translation_id] != rating:
            raise ValueError("A translation cannot have conflicting ratings in one ballot")
        ratings[translation_id] = rating
    if not ratings:
        raise ValueError("A ballot must contain at least one rating")
    return sorted(ratings.items())


def _ballot_fingerprint(canonical_votes: list[tuple[int, int]]) -> str:
    payload = "|".join(f"{translation_id}:{rating}" for translation_id, rating in canonical_votes)
    return sha256(payload.encode()).hexdigest()


def process_votes(
    user_id: int,
    query_id: int,
    votes_data,
    observed_at: datetime | None = None,
) -> dict[str, bool | str]:
    """
    Process votes for a query from a user.

    Args:
        user_id (int): The ID of the user casting votes
        query_id (int): The ID of the query being voted on
        votes_data (list): List of vote dictionaries with keys:
            - translation_id (int): ID of the translation being voted on
            - rating (int): Rating value (3=Excellent, 2=Meaning Correct, 1=Understandable, -1=Trash)

    Returns:
        dict: Result of the voting process
    """
    session = cast(Session, db_session)
    try:
        canonical = _canonical_votes(votes_data)
        translation_ids = {translation_id for translation_id, _ in canonical}
        translations = session.query(Translation).filter(Translation.id.in_(translation_ids)).all()
        translation_map = {translation.id: translation for translation in translations}
        if set(translation_map) != translation_ids or any(t.query_id != query_id for t in translations):
            raise ValueError("Every rated translation must belong to the ballot query")

        vote_repo = VoteRepository(session)
        existing_votes = vote_repo.get_by_user_and_query(user_id, query_id)
        vote_map = {v.translation_id: v for v in existing_votes}
        conflicts = [
            translation_id
            for translation_id, rating in canonical
            if translation_id in vote_map and vote_map[translation_id].rating != rating
        ]
        if conflicts:
            raise ValueError("Ratings are immutable; use the correction command for exceptional changes")

        new_items = [(translation_id, rating) for translation_id, rating in canonical if translation_id not in vote_map]
        if not new_items:
            return {"success": True, "message": "Identical ballot already recorded"}

        observed_at = observed_at or datetime.now(UTC)
        ballot = RatingBallot(
            user_id=user_id,
            query_id=query_id,
            fingerprint=_ballot_fingerprint(canonical),
            observed_at=observed_at,
            is_synthetic=False,
        )
        session.add(ballot)
        session.flush()
        for translation_id, rating in new_items:
            vote = Vote(
                user_id=user_id,
                query_id=query_id,
                translation_id=translation_id,
                rating=rating,
                ballot_id=ballot.id,
                created_at=observed_at,
            )
            session.add(vote)
            vote_map[translation_id] = vote
        session.flush()

        _derive_pairwise_from_votes(
            session,
            user_id,
            query_id,
            [
                {"translation_id": vote.translation_id, "rating": vote.rating}
                for vote in vote_map.values()
                if vote.rating is not None
            ],
            ballot=ballot,
            new_translation_ids={translation_id for translation_id, _ in new_items},
        )
        session.commit()

    except ValueError as error:
        session.rollback()
        return {"success": False, "error": str(error)}
    except Exception:
        session.rollback()
        logger.exception("Error processing votes")
        return {"success": False, "error": "An error occurred while processing votes"}

    else:
        invalidate_caches()
        return {"success": True, "message": "Votes processed successfully"}


def _derive_pairwise_from_votes(
    session: Session,
    user_id: int,
    query_id: int,
    votes_data,
    query_difficulty: str = "unknown",
    ballot: RatingBallot | None = None,
    new_translation_ids: set[int] | None = None,
) -> None:
    """Derive pairwise comparisons from star rating votes.

    New ballot periods compare newly observed translations with each other and
    with existing anchors. Historical derived evidence is never rewritten.
    """
    elo_service = get_elo_service(session)

    # Pre-fetch translations to avoid N+1 query
    translation_ids = {v["translation_id"] for v in votes_data if v.get("translation_id")}
    translations = session.query(Translation).filter(Translation.id.in_(translation_ids)).all()
    translation_map = {t.id: t for t in translations}

    participant_count = len(translation_map)
    evidence_weight = 1.0 / max(1, participant_count - 1)
    games: list[tuple[str, str, float, float]] = []
    for v1, v2 in combinations(sorted(votes_data, key=lambda vote: vote["translation_id"]), 2):
        if new_translation_ids is not None and not (
            v1["translation_id"] in new_translation_ids or v2["translation_id"] in new_translation_ids
        ):
            continue
        t1 = translation_map.get(v1["translation_id"])
        t2 = translation_map.get(v2["translation_id"])

        if not t1 or not t2:
            continue
        if t1.model == t2.model:
            continue

        r1, r2 = v1["rating"], v2["rating"]

        # Check tie-skip logic (difficulty-aware: 3★/3★ skipped on easy/unknown, tied on medium/hard)
        if _should_skip_pair(r1, r2, query_difficulty):
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
            # Equal ratings: tie (0.5) for 1-star and 2-star
            winner_model = None
            loser_model = None
            score = 0.5

        try:
            # Store comparison without incremental rating update;
            # ratings are rebuilt from all comparisons below.
            comp = PairwiseComparison(
                query_id=query_id,
                user_id=user_id,
                winner_model=winner_model,
                loser_model=loser_model,
                translation_a_id=v1["translation_id"],
                translation_b_id=v2["translation_id"],
                source="derived",
                score=score,
                evidence_weight=evidence_weight,
                ballot_id=ballot.id if ballot else None,
                created_at=ballot.observed_at if ballot else datetime.now(UTC),
            )
            session.add(comp)
            session.flush()
            model_a = winner_model or str(t1.model)
            model_b = loser_model or str(t2.model)
            games.append((model_a, model_b, score, evidence_weight))
        except Exception:
            logger.exception(
                "Error recording pairwise comparison for %s vs %s",
                t1.model,
                t2.model,
            )

    observed_at = ballot.observed_at if ballot else datetime.now(UTC)
    elo_service.apply_rating_period(games, observed_at)


def correct_vote(user_id: int, query_id: int, translation_id: int, rating: int) -> None:
    """Exceptional maintenance path for correcting one mistaken ballot value."""
    if rating not in (3, 2, 1, -1):
        raise ValueError("Rating must be one of 3, 2, 1, or -1")
    session = cast(Session, db_session)
    try:
        vote = (
            session.query(Vote)
            .filter(
                Vote.user_id == user_id,
                Vote.query_id == query_id,
                Vote.translation_id == translation_id,
            )
            .one_or_none()
        )
        if not vote or not vote.ballot:
            raise ValueError("Vote or its rating ballot was not found")
        if vote.rating == rating:
            return

        ballot = vote.ballot
        vote.rating = rating
        corrected_values = sorted(
            (item.translation_id, rating if item.id == vote.id else item.rating)
            for item in ballot.votes
            if item.rating is not None
        )
        ballot.fingerprint = _ballot_fingerprint(corrected_values)
        session.query(PairwiseComparison).filter(
            PairwiseComparison.source == "derived",
            PairwiseComparison.ballot_id == ballot.id,
        ).delete()
        all_votes = session.query(Vote).filter(Vote.user_id == user_id, Vote.query_id == query_id).all()
        ballot_translation_ids = {item.translation_id for item in ballot.votes}
        _derive_pairwise_from_votes(
            session,
            user_id,
            query_id,
            [
                {"translation_id": item.translation_id, "rating": item.rating}
                for item in all_votes
                if item.rating is not None
            ],
            ballot=ballot,
            new_translation_ids=ballot_translation_ids,
        )
        get_elo_service(session).rebuild_ratings_from_comparisons()
        invalidate_caches()
    except Exception:
        session.rollback()
        raise
