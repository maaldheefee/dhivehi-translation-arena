from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime, default=func.now())

    translations = relationship("Translation", back_populates="query", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="query", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Query id={self.id} source_text={self.source_text[:20]}...>"


class RatingBallot(Base):
    """Immutable star-rating evidence submitted at one observation time."""

    __tablename__ = "rating_ballots"
    __table_args__ = (
        UniqueConstraint("user_id", "query_id", "fingerprint", name="unique_rating_ballot_fingerprint"),
        Index("ix_rating_ballots_observed", "observed_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("queries.id"), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=func.now())

    votes = relationship("Vote", back_populates="ballot")
    comparisons = relationship("PairwiseComparison", back_populates="ballot")


class Translation(Base):
    __tablename__ = "translations"
    __table_args__ = (
        Index("ix_translations_model", "model"),
        Index("ix_translations_query_model", "query_id", "model"),
        Index("ix_translations_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("queries.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)  # Who generated this
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    translation: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # For blind testing, position in the UI (1, 2, or 3)
    cost: Mapped[float] = mapped_column(Float, default=0.0)  # Cost of the API call
    response_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=func.now())

    query = relationship("Query", back_populates="translations")
    user = relationship("User")
    votes = relationship("Vote", back_populates="translation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Translation id={self.id} model={self.model}>"


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "query_id",
            "translation_id",
            name="unique_user_query_translation_vote",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    translation_id: Mapped[int] = mapped_column(Integer, ForeignKey("translations.id"), nullable=False)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("queries.id"), nullable=False)
    rating: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # 3=Excellent, 2=Good/Meaning Correct, 1=Okay/Understandable, -1=Trash
    ballot_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("rating_ballots.id"), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=func.now())

    user = relationship("User")
    translation = relationship("Translation", back_populates="votes")
    query = relationship("Query", back_populates="votes")
    ballot = relationship("RatingBallot", back_populates="votes")

    def __repr__(self) -> str:
        return f"<Vote id={self.id} user_id={self.user_id} query_id={self.query_id} translation_id={self.translation_id} rating={self.rating}>"


class PairwiseComparison(Base):
    """Records pairwise comparison results between two translations.

    Comparisons can come from:
    - 'derived': Inferred from star ratings (if A=3★, B=1★ → A wins)
    - 'explicit': Direct user choice in Quick Compare mode

    The `score` column stores the fractional Glicko-2 game score on [0, 1]:
    - Derived: gap-based fractional score (0.70, 0.85, 0.95, 1.0)
    - Explicit: binary (1.0 for win, 0.0 for loss, 0.5 for tie)
    Winner gets `score`, loser gets `1 - score`.
    """

    __tablename__ = "pairwise_comparisons"
    __table_args__ = (Index("ix_pairwise_user_source", "user_id", "source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("queries.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    winner_model: Mapped[str | None] = mapped_column(String(50), nullable=True)  # NULL = tie
    loser_model: Mapped[str | None] = mapped_column(String(50), nullable=True)  # NULL = tie
    translation_a_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("translations.id"), nullable=True)
    translation_b_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("translations.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # 'derived' or 'explicit'
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # Glicko-2 game score [0, 1]
    evidence_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    ballot_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("rating_ballots.id"), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=func.now())

    query = relationship("Query")
    user = relationship("User")
    translation_a = relationship("Translation", foreign_keys=[translation_a_id])
    translation_b = relationship("Translation", foreign_keys=[translation_b_id])
    ballot = relationship("RatingBallot", back_populates="comparisons")

    def __repr__(self) -> str:
        return f"<PairwiseComparison id={self.id} winner={self.winner_model} loser={self.loser_model}>"


class ModelELO(Base):
    """Stores Glicko-2 ratings and win/loss statistics for each model.

    Columns:
    - elo_rating: Glicko-2 rating (µ), renamed from ELO but field name kept for compatibility
    - rating_deviation: Glicko-2 RD (φ), uncertainty measure. Starts at 350, floor at 80.
    - volatility: Glicko-2 sigma, rating stability over time.
    - legacy_elo_rating: Pre-migration ELO rating, preserved for rollback.
    - last_comparison_at: Timestamp of last comparison, used for RD time decay.
    """

    __tablename__ = "model_elo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    elo_rating: Mapped[float] = mapped_column(Float, default=1500.0)  # Glicko-2 rating (µ)
    rating_deviation: Mapped[float] = mapped_column(Float, default=350.0)  # Glicko-2 RD (φ)
    volatility: Mapped[float] = mapped_column(Float, default=0.06)  # Glicko-2 volatility (σ)
    legacy_elo_rating: Mapped[float | None] = mapped_column(Float, nullable=True)  # Pre-migration ELO for rollback
    last_comparison_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # For RD time decay
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    ties: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<ModelELO model={self.model} rating={self.elo_rating} rd={self.rating_deviation}>"

    @property
    def total_matches(self) -> int:
        """Total number of matches this model has participated in."""
        return self.wins + self.losses + self.ties

    @property
    def win_rate(self) -> float:
        """Win rate as a fraction (0.0 to 1.0)."""
        total = self.total_matches
        if total == 0:
            return 0.0
        return self.wins / total
