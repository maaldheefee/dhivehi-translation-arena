from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

engine = None
SessionFactory = sessionmaker(autocommit=False, autoflush=False)
db_session = scoped_session(SessionFactory)
Base = declarative_base()
Base.query = db_session.query_property()


def init_db(app):
    global engine  # noqa: PLW0603
    engine = create_engine(app.config["DATABASE_URI"])

    if app.config["DATABASE_URI"].startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    db_session.configure(bind=engine)
    Base.metadata.bind = engine


def shutdown_session(exception=None):
    db_session.remove()
