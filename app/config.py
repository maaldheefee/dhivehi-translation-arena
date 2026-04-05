"""Centralized configuration for Dhivehi Translation Arena."""

import os
import warnings
from pathlib import Path
from typing import Any, ClassVar, NotRequired, TypedDict

import yaml


class ModelConfig(TypedDict):
    """Configuration for a model definition."""

    name: str
    display_name: str
    type: str
    input_cost_per_mtok: float
    output_cost_per_mtok: float
    is_active: bool
    is_hidden: NotRequired[bool]  # Hidden from UI selectors but data preserved
    rate_limit: NotRequired[float | None]
    thinking_budget: NotRequired[int | None]
    temperature: NotRequired[float | None]
    reasoning: NotRequired[dict[str, Any]]
    preset_name: NotRequired[str | None]
    base_model: NotRequired[str | None]
    timeout: NotRequired[float]  # API timeout in seconds, default 90


_REQUIRED_MODEL_FIELDS = frozenset({
    "name",
    "display_name",
    "type",
    "input_cost_per_mtok",
    "output_cost_per_mtok",
    "is_active",
})


def _resolve_models_path() -> Path:
    return Path(__file__).resolve().parent.parent / "models.yaml"


def _load_models_from_yaml(path: Path | None = None) -> dict[str, ModelConfig]:
    if path is None:
        path = _resolve_models_path()

    if not path.exists():
        msg = f"models.yaml not found at {path}"
        raise FileNotFoundError(msg)

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or len(data) == 0:
        msg = f"models.yaml must contain a non-empty mapping, got {type(data).__name__}"
        raise ValueError(msg)

    models: dict[str, ModelConfig] = {}
    errors: list[str] = []

    for key, entry in data.items():
        if not isinstance(entry, dict):
            errors.append(f"Model '{key}': expected mapping, got {type(entry).__name__}")
            continue

        missing = _REQUIRED_MODEL_FIELDS - set(entry)
        if missing:
            errors.append(f"Model '{key}': missing required fields: {', '.join(sorted(missing))}")
            continue

        if not isinstance(entry["is_active"], bool):
            errors.append(f"Model '{key}': 'is_active' must be a boolean")
            continue

        if not isinstance(entry["input_cost_per_mtok"], (int, float)):
            errors.append(f"Model '{key}': 'input_cost_per_mtok' must be a number")
            continue

        if not isinstance(entry["output_cost_per_mtok"], (int, float)):
            errors.append(f"Model '{key}': 'output_cost_per_mtok' must be a number")
            continue

        models[key] = entry  # type: ignore[assignment]

    if errors:
        error_text = "\n  ".join(errors)
        msg = f"Invalid models.yaml:\n  {error_text}"
        raise ValueError(msg)

    return models


class Config:
    """Base configuration class."""

    # Environment variables
    OPENROUTER_API_KEY: ClassVar[str | None] = os.environ.get("OPENROUTER_API_KEY")

    # Database
    DATA_DIR: ClassVar[str] = os.environ.get("DATA_DIR", "data")
    DATABASE_URI: ClassVar[str] = os.environ.get(
        "DATABASE_URI", f"sqlite:///{DATA_DIR}/dhivehi_translation_arena.db"
    )

    # Application settings
    SECRET_KEY: ClassVar[str] = os.environ.get(
        "SECRET_KEY", "dev-secret-key-change-in-production"
    )

    @classmethod
    def check_configuration(cls) -> None:
        """Check for critical configuration issues."""
        if (
            os.environ.get("FLASK_ENV") == "production"
            and cls.SECRET_KEY == "dev-secret-key-change-in-production"
        ):
            warnings.warn(
                "SECRET_KEY is set to default value in production! This is a security risk.",
                UserWarning,
                stacklevel=2,
            )

    MAX_CACHE_SIZE: ClassVar[int] = int(os.environ.get("MAX_CACHE_SIZE", "100"))
    MAX_MODELS_SELECTION: ClassVar[int] = int(
        os.environ.get("MAX_MODELS_SELECTION", "6")
    )

    # Translation settings
    SYSTEM_PROMPT: ClassVar[str] = (
        "Translate to Dhivehi. Don't explain. Only return the translated text."
    )

    # Model configurations loaded from models.yaml
    MODELS: ClassVar[dict[str, ModelConfig]] = _load_models_from_yaml()

    # API settings
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    # Functionality settings
    DEFAULT_TEMPERATURE = 0.1  # Changed from 0.85 to 0.1
    MAX_OUTPUT_TOKENS = 4096


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get("SECRET_KEY")


class TestingConfig(Config):
    """Testing configuration."""

    DEBUG = True
    TESTING = True
    DATABASE_URI = "sqlite:///:memory:"


# Configuration mapping
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config(config_name: str | None = None) -> Config:
    """Get configuration instance."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")
    return config.get(config_name, config["default"])()
