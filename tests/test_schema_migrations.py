"""Tests for additive, repeatable rating-evidence migrations."""

from sqlalchemy import create_engine, inspect, text

from app.schema_migrations import run_schema_migrations


def test_legacy_votes_are_backfilled_into_one_synthetic_ballot():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE queries (id INTEGER PRIMARY KEY, timestamp DATETIME)"))
        connection.execute(
            text("CREATE TABLE translations (id INTEGER PRIMARY KEY, query_id INTEGER, created_at DATETIME)")
        )
        connection.execute(
            text(
                """
                CREATE TABLE votes (
                    id INTEGER PRIMARY KEY, user_id INTEGER, query_id INTEGER,
                    translation_id INTEGER, rating INTEGER
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE pairwise_comparisons (
                    id INTEGER PRIMARY KEY, user_id INTEGER, query_id INTEGER,
                    source VARCHAR(20), created_at DATETIME
                )
                """
            )
        )
        connection.execute(text("INSERT INTO users VALUES (1)"))
        connection.execute(text("INSERT INTO queries VALUES (10, '2025-01-03 00:00:00')"))
        connection.execute(text("INSERT INTO translations VALUES (100, 10, '2025-01-02 00:00:00')"))
        connection.execute(text("INSERT INTO translations VALUES (101, 10, '2025-01-02 00:00:00')"))
        connection.execute(text("INSERT INTO votes VALUES (1, 1, 10, 100, 3)"))
        connection.execute(text("INSERT INTO votes VALUES (2, 1, 10, 101, 2)"))
        connection.execute(text("INSERT INTO pairwise_comparisons VALUES (1, 1, 10, 'derived', '2025-01-04 00:00:00')"))

    run_schema_migrations(engine)
    run_schema_migrations(engine)

    assert {column["name"] for column in inspect(engine).get_columns("votes")} >= {"ballot_id", "created_at"}
    with engine.connect() as connection:
        ballots = connection.execute(
            text("SELECT id, fingerprint, observed_at, is_synthetic FROM rating_ballots")
        ).all()
        votes = connection.execute(text("SELECT ballot_id, created_at FROM votes ORDER BY id")).all()
        comparison_ballot = connection.execute(text("SELECT ballot_id FROM pairwise_comparisons")).scalar_one()

    assert len(ballots) == 1
    assert ballots[0].fingerprint == "legacy:1:10"
    assert ballots[0].is_synthetic == 1
    assert votes == [(ballots[0].id, "2025-01-04 00:00:00")] * 2
    assert comparison_ballot == ballots[0].id
