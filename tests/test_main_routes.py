import json
from types import SimpleNamespace

from flask import Flask

from app.blueprints import main as main_module
from app.services.acquisition_policy import EvaluationSession


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
