from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker


class Base(DeclarativeBase):
    pass


engine: Engine | None = None
SessionFactory = sessionmaker(autocommit=False, autoflush=False)
db_session = scoped_session(SessionFactory)


def init_db(app) -> None:
    global engine
    engine = create_engine(app.config["DATABASE_URI"])

    if app.config["DATABASE_URI"].startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    db_session.configure(bind=engine)

    from app.schema_migrations import run_schema_migrations

    run_schema_migrations(engine)


def shutdown_session(exception=None) -> None:
    db_session.remove()
