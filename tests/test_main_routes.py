import json
from types import SimpleNamespace

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from app.blueprints import main as main_module
from app.database import Base
from app.models import Query, Translation, User, Vote
from app.services import vote_service
from app.services.acquisition_policy import EvaluationSession
from app.services.judge_service import JudgeResult


def _app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test"
    app.register_blueprint(main_module.main_bp)
    return app


def _config():
    return SimpleNamespace(
        MAX_MODELS_SELECTION=6,
        MODELS={
            "target": {"input_cost_per_mtok": 1, "output_cost_per_mtok": 2},
            "anchor": {"input_cost_per_mtok": 3, "output_cost_per_mtok": 4},
            "hidden": {"input_cost_per_mtok": 5, "output_cost_per_mtok": 6},
        },
    )


def test_index_renders_the_evaluation_session_selected_by_the_policy(monkeypatch):
    monkeypatch.setattr(main_module, "get_config", _config)
    monkeypatch.setattr(
        main_module,
        "get_available_models",
        lambda: {"target": "Target", "anchor": "Anchor", "hidden": "Hidden"},
    )
    monkeypatch.setattr(main_module, "get_model_usage_stats", dict)
    monkeypatch.setattr(main_module, "check_user_budget", lambda _username: (True, 0.0))
    monkeypatch.setattr(
        main_module,
        "_evaluation_session",
        lambda *_args, **_kwargs: EvaluationSession(("target", "anchor"), ("chosen-query",)),
    )
    monkeypatch.setattr(main_module.random, "shuffle", lambda _items: None)
    monkeypatch.setattr(
        main_module,
        "render_template",
        lambda _template, **context: json.dumps(
            {
                "queries": context["predefined_queries"],
                "models": list(context["available_models"]),
            }
        ),
    )

    response = _app().test_client().get("/")

    assert json.loads(response.get_data(as_text=True)) == {
        "queries": ["chosen-query"],
        "models": ["target", "anchor"],
    }


def test_available_models_preserves_hidden_exclusions_and_requested_count(monkeypatch):
    captured = {}
    monkeypatch.setattr(main_module, "get_config", _config)
    monkeypatch.setattr(
        main_module,
        "get_available_models",
        lambda: {"target": "Target", "anchor": "Anchor", "hidden": "Hidden"},
    )
    monkeypatch.setattr(main_module, "get_model_usage_stats", lambda: {"target": 0, "anchor": 10, "hidden": 20})

    def evaluation_session(*_args, **kwargs):
        captured.update(kwargs)
        return EvaluationSession(("target", "anchor"), ())

    monkeypatch.setattr(main_module, "_evaluation_session", evaluation_session)

    response = _app().test_client().get("/get_available_models?hidden=hidden&count=2")
    payload = response.get_json()

    assert captured["excluded_models"] == {"hidden"}
    assert captured["max_models"] == 2
    assert payload["models"]["target"]["selected"] is True
    assert payload["models"]["anchor"]["selected"] is True
    assert payload["models"]["hidden"]["selected"] is False


def test_direct_judge_returns_verdict_and_accumulates_session_cost(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    database = scoped_session(sessionmaker(bind=engine))
    user = User(username="judge-user", password_hash="x")
    query = Query(source_text="source")
    database.add_all([user, query])
    database.flush()
    translations = [
        Translation(
            query_id=query.id,
            model=f"model-{position}",
            translation=f"translation-{position}",
            system_prompt="sp",
            position=position,
            user_id=user.id,
        )
        for position in (1, 2)
    ]
    database.add_all(translations)
    database.commit()
    monkeypatch.setattr(main_module, "db_session", database)
    monkeypatch.setattr(
        main_module,
        "judge_translations",
        lambda *_args: JudgeResult(winner="b", comments="B is more accurate.", cost=0.000123),
    )
    client = _app().test_client()
    with client.session_transaction() as browser_session:
        browser_session["username"] = user.username
        browser_session["comparison_judge_cost"] = 0.0001

    response = client.post(
        "/compare/judge",
        json={"query_id": query.id, "translation_ids": [translations[0].id, translations[1].id]},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "winner": "b",
        "comments": "B is more accurate.",
        "cost": 0.000123,
        "session_total_cost": 0.000223,
        "model": "google/gemini-3.7-flash",
    }


def test_direct_judge_rejects_translations_from_another_query(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    database = scoped_session(sessionmaker(bind=engine))
    user = User(username="judge-user", password_hash="x")
    queries = [Query(source_text="first"), Query(source_text="second")]
    database.add_all([user, *queries])
    database.flush()
    translations = [
        Translation(
            query_id=query.id,
            model=f"model-{position}",
            translation=f"translation-{position}",
            system_prompt="sp",
            position=position,
            user_id=user.id,
        )
        for position, query in enumerate(queries, 1)
    ]
    database.add_all(translations)
    database.commit()
    monkeypatch.setattr(main_module, "db_session", database)
    client = _app().test_client()
    with client.session_transaction() as browser_session:
        browser_session["username"] = user.username

    response = client.post(
        "/compare/judge",
        json={"query_id": queries[0].id, "translation_ids": [translations[0].id, translations[1].id]},
    )

    assert response.status_code == 400


def test_vote_rejects_mixed_query_ballot_as_bad_request_without_writes(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    database = scoped_session(sessionmaker(bind=engine))
    user = User(username="tester", password_hash="x")
    first_query = Query(source_text="first")
    second_query = Query(source_text="second")
    database.add_all([user, first_query, second_query])
    database.flush()
    translations = [
        Translation(
            query_id=query.id,
            model=f"model-{position}",
            translation=f"translation-{position}",
            system_prompt="sp",
            position=position,
            user_id=user.id,
        )
        for position, query in enumerate((first_query, second_query), 1)
    ]
    database.add_all(translations)
    database.commit()
    monkeypatch.setattr(main_module, "db_session", database)
    monkeypatch.setattr(vote_service, "db_session", database)
    client = _app().test_client()
    with client.session_transaction() as browser_session:
        browser_session["username"] = user.username

    response = client.post(
        "/vote",
        json={
            "query_id": first_query.id,
            "votes": [
                {"translation_id": translations[0].id, "rating": 3},
                {"translation_id": translations[1].id, "rating": 2},
            ],
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Every rated translation must belong to the ballot query"}
    assert database.query(Vote).count() == 0
    database.remove()


def test_vote_accepts_numeric_string_query_id_from_browser(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    database = scoped_session(sessionmaker(bind=engine))
    user = User(username="tester", password_hash="x")
    query = Query(source_text="query")
    database.add_all([user, query])
    database.flush()
    translation = Translation(
        query_id=query.id,
        model="model",
        translation="translation",
        system_prompt="sp",
        position=1,
        user_id=user.id,
    )
    database.add(translation)
    database.commit()
    monkeypatch.setattr(main_module, "db_session", database)
    monkeypatch.setattr(vote_service, "db_session", database)
    client = _app().test_client()
    with client.session_transaction() as browser_session:
        browser_session["username"] = user.username

    response = client.post(
        "/vote",
        json={
            "query_id": str(query.id),
            "votes": [{"translation_id": translation.id, "rating": 3}],
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "success"}
    assert database.query(Vote).count() == 1
    database.remove()
