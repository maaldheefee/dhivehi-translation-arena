from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Query
from app.repositories.query_repository import QueryRepository
from app.services import translation_service


class _TranslationClient:
    SYSTEM_PROMPT = "test prompt"

    def translate(self, source_text: str) -> tuple[str, float]:
        return f"translated: {source_text}", 0.0


def test_concurrent_translation_workers_reuse_the_winning_query(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'translations.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    first_lookups = Barrier(2)
    lookup_count = 0
    lookup_lock = Lock()
    original_lookup = QueryRepository.get_by_source_text

    def synchronized_initial_lookup(repository, source_text):
        nonlocal lookup_count
        with lookup_lock:
            lookup_count += 1
            current_lookup = lookup_count
        result = original_lookup(repository, source_text)
        if current_lookup <= 2:
            first_lookups.wait()
        return result

    monkeypatch.setattr(translation_service, "SessionFactory", sessions)
    monkeypatch.setattr(translation_service, "get_translation_client", lambda _model: _TranslationClient())
    monkeypatch.setattr(QueryRepository, "get_by_source_text", synchronized_initial_lookup)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda model: translation_service.get_translation_for_model("same source", model, 1),
                ("model-a", "model-b"),
            )
        )

    with sessions() as session:
        queries = session.query(Query).all()

    assert len(queries) == 1
    assert {result["query_id"] for result in results} == {queries[0].id}
