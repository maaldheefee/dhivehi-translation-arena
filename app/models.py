from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(256), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"


class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True)
    source_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())

    translations = relationship(
        "Translation", back_populates="query", cascade="all, delete-orphan"
    )
    votes = relationship("Vote", back_populates="query", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Query id={self.id} source_text={self.source_text[:20]}...>"


class Translation(Base):
    __tablename__ = "translations"

    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Who generated this
    model = Column(String(50), nullable=False)
    translation = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=False)
    position = Column(
        Integer, nullable=False
    )  # For blind testing, position in the UI (1, 2, or 3)
    cost = Column(Float, default=0.0)  # Cost of the API call
    response_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=func.now())

    query = relationship("Query", back_populates="translations")
    user = relationship("User")
    votes = relationship(
        "Vote", back_populates="translation", cascade="all, delete-orphan"
    )

    def __repr__(self):
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

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    translation_id = Column(Integer, ForeignKey("translations.id"), nullable=False)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    rating = Column(Integer, nullable=True)  # 3=Excellent, 2=Good/Meaning Correct, 1=Okay/Understandable, -1=Trash

    user = relationship("User")
    translation = relationship("Translation", back_populates="votes")
    query = relationship("Query", back_populates="votes")

    def __repr__(self):
        return f"<Vote id={self.id} user_id={self.user_id} query_id={self.query_id} translation_id={self.translation_id} rating={self.rating}>"


class PairwiseComparison(Base):
    """Records pairwise comparison results between two translations.

    Comparisons can come from:
    - 'derived': Inferred from star ratings (if A=3★, B=1★ → A wins)
    - 'explicit': Direct user choice in Quick Compare mode
    """

    __tablename__ = "pairwise_comparisons"

    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    winner_model = Column(String(50), nullable=True)  # NULL = tie
    loser_model = Column(String(50), nullable=True)  # NULL = tie
    translation_a_id = Column(Integer, ForeignKey("translations.id"), nullable=True)
    translation_b_id = Column(Integer, ForeignKey("translations.id"), nullable=True)
    source = Column(String(20), nullable=False)  # 'derived' or 'explicit'
    created_at = Column(DateTime, default=func.now())

    query = relationship("Query")
    user = relationship("User")
    translation_a = relationship("Translation", foreign_keys=[translation_a_id])
    translation_b = relationship("Translation", foreign_keys=[translation_b_id])

    def __repr__(self):
        return f"<PairwiseComparison id={self.id} winner={self.winner_model} loser={self.loser_model}>"


class ModelELO(Base):
    """Stores ELO ratings and win/loss statistics for each model."""

    __tablename__ = "model_elo"

    id = Column(Integer, primary_key=True)
    model = Column(String(50), nullable=False, unique=True)
    elo_rating = Column(Float, default=1500.0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ModelELO model={self.model} elo={self.elo_rating}>"

    @property
    def total_matches(self):
        """Total number of matches this model has participated in."""
        return (self.wins or 0) + (self.losses or 0) + (self.ties or 0)

    @property
    def win_rate(self):
        """Win rate as a fraction (0.0 to 1.0)."""
        total = self.total_matches
        if total == 0:
            return 0.0
        return (self.wins or 0) / total
