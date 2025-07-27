from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

engine = None
SessionFactory = sessionmaker(autocommit=False, autoflush=False)
db_session = scoped_session(SessionFactory)
Base = declarative_base()
Base.query = db_session.query_property()


def init_db(app):
    global engine
    engine = create_engine(app.config["DATABASE_URI"])
    db_session.configure(bind=engine)
    Base.metadata.bind = engine


def shutdown_session(exception=None):
    db_session.remove()
