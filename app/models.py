from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"


class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    is_predefined = Column(Integer, default=0)  # 0 = user-supplied, 1 = predefined
    created_at = Column(DateTime, default=func.now())

    translations = relationship(
        "Translation", back_populates="query", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Query id={self.id} text={self.text[:20]}...>"


class Translation(Base):
    __tablename__ = "translations"

    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    model = Column(String(50), nullable=False)
    translation = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=False)
    position = Column(
        Integer, nullable=False
    )  # For blind testing, position in the UI (1, 2, or 3)
    cost = Column(Float, default=0.0)  # Cost of the API call
    created_at = Column(DateTime, default=func.now())

    query = relationship("Query", back_populates="translations")
    votes = relationship(
        "Vote", back_populates="translation", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Translation id={self.id} model={self.model}>"


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    translation_id = Column(Integer, ForeignKey("translations.id"), nullable=False)
    user = Column(
        String(50), nullable=False
    )  # Changed from 36 to 50 to accommodate usernames
    created_at = Column(DateTime, default=func.now())

    translation = relationship("Translation", back_populates="votes")

    def __repr__(self):
        return (
            f"<Vote id={self.id} translation_id={self.translation_id} user={self.user}>"
        )
