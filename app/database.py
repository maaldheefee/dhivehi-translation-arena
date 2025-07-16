import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

# It's better to get this from a config, but for now, to match the existing
# structure, we'll define it here.
DATABASE_URI = os.environ.get("DATABASE_URI", "sqlite:///data/translations.db")

engine = create_engine(DATABASE_URI)
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)
Base = declarative_base()
Base.query = db_session.query_property()


def teardown_db_session(exception=None):
    """Remove the database session."""
    db_session.remove()
