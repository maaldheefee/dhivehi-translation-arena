"""Small idempotent schema migrations for this personal SQLite application."""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import Engine, Table, inspect, text


def _columns(engine: Engine, table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def _add_column(engine: Engine, table: str, definition: str) -> None:
    name = definition.split()[0]
    if name not in _columns(engine, table):
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))


def run_schema_migrations(engine: Engine) -> None:
    """Add ballot metadata and deterministically backfill legacy vote groups."""
    tables = set(inspect(engine).get_table_names())
    if "translations" in tables:
        from app.models import JudgeCall

        cast(Table, JudgeCall.__table__).create(bind=engine, checkfirst=True)
        for definition in (
            "cost_source VARCHAR(30) NOT NULL DEFAULT 'estimated'",
            "input_word_count INTEGER",
            "generation_id VARCHAR(80)",
            "served_model VARCHAR(120)",
            "provider_name VARCHAR(120)",
            "service_tier VARCHAR(30)",
            "prompt_tokens INTEGER",
            "completion_tokens INTEGER",
            "reasoning_tokens INTEGER",
            "cached_tokens INTEGER",
        ):
            _add_column(engine, "translations", definition)

    if "votes" not in tables:
        return

    from app.models import RatingBallot

    cast(Table, RatingBallot.__table__).create(bind=engine, checkfirst=True)
    _add_column(engine, "votes", "ballot_id INTEGER REFERENCES rating_ballots(id)")
    _add_column(engine, "votes", "created_at DATETIME")

    if "pairwise_comparisons" in tables:
        _add_column(engine, "pairwise_comparisons", "evidence_weight FLOAT NOT NULL DEFAULT 1.0")
        _add_column(engine, "pairwise_comparisons", "ballot_id INTEGER REFERENCES rating_ballots(id)")

    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    with engine.begin() as connection:
        groups = connection.execute(
            text(
                """
                SELECT v.user_id, v.query_id,
                       COALESCE(MIN(pc.created_at), MIN(t.created_at), MIN(q.timestamp), :epoch) AS observed_at
                FROM votes v
                JOIN queries q ON q.id = v.query_id
                LEFT JOIN translations t ON t.id = v.translation_id
                LEFT JOIN pairwise_comparisons pc
                  ON pc.user_id = v.user_id AND pc.query_id = v.query_id AND pc.source = 'derived'
                WHERE v.ballot_id IS NULL
                GROUP BY v.user_id, v.query_id
                """
            ),
            {"epoch": epoch},
        ).all()

        for user_id, query_id, observed_at in groups:
            fingerprint = f"legacy:{user_id}:{query_id}"
            connection.execute(
                text(
                    """
                    INSERT INTO rating_ballots
                        (user_id, query_id, fingerprint, observed_at, is_synthetic, created_at)
                    SELECT :user_id, :query_id, :fingerprint, :observed_at, 1, :observed_at
                    WHERE NOT EXISTS (
                        SELECT 1 FROM rating_ballots
                        WHERE user_id = :user_id AND query_id = :query_id AND fingerprint = :fingerprint
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "query_id": query_id,
                    "fingerprint": fingerprint,
                    "observed_at": observed_at,
                },
            )
            ballot_id = connection.execute(
                text(
                    """
                    SELECT id FROM rating_ballots
                    WHERE user_id = :user_id AND query_id = :query_id AND fingerprint = :fingerprint
                    """
                ),
                {"user_id": user_id, "query_id": query_id, "fingerprint": fingerprint},
            ).scalar_one()
            connection.execute(
                text(
                    """
                    UPDATE votes SET ballot_id = :ballot_id, created_at = COALESCE(created_at, :observed_at)
                    WHERE user_id = :user_id AND query_id = :query_id AND ballot_id IS NULL
                    """
                ),
                {
                    "ballot_id": ballot_id,
                    "observed_at": observed_at,
                    "user_id": user_id,
                    "query_id": query_id,
                },
            )
            if "pairwise_comparisons" in tables:
                participant_count = connection.execute(
                    text("SELECT COUNT(*) FROM votes WHERE user_id = :user_id AND query_id = :query_id"),
                    {"user_id": user_id, "query_id": query_id},
                ).scalar_one()
                connection.execute(
                    text(
                        """
                        UPDATE pairwise_comparisons
                        SET ballot_id = :ballot_id, evidence_weight = :evidence_weight
                        WHERE user_id = :user_id AND query_id = :query_id
                          AND source = 'derived' AND ballot_id IS NULL
                        """
                    ),
                    {
                        "ballot_id": ballot_id,
                        "evidence_weight": 1.0 / max(1, participant_count - 1),
                        "user_id": user_id,
                        "query_id": query_id,
                    },
                )
