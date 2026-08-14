"""Centralized configuration for Dhivehi Translation Arena."""

import logging
import os
import threading
import warnings
from pathlib import Path
from typing import Any, ClassVar, NotRequired, TypedDict

import yaml

logger = logging.getLogger(__name__)


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
    deactivation_reason: NotRequired[str | None]  # Shown as tooltip for inactive models


_REQUIRED_MODEL_FIELDS = frozenset(
    {
        "name",
        "display_name",
        "type",
        "input_cost_per_mtok",
        "output_cost_per_mtok",
        "is_active",
    }
)


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

        models[key] = entry

    if errors:
        error_text = "\n  ".join(errors)
        msg = f"Invalid models.yaml:\n  {error_text}"
        raise ValueError(msg)

    return models


class _ModelsReloader:
    """Keep a last-known-good model snapshot and refresh it when the file changes."""

    def __init__(self, path: Path, models: dict[str, ModelConfig]) -> None:
        self._path = path
        self._models = models
        self._lock = threading.Lock()
        self._observed_version = self._file_version()

    def _file_version(self) -> tuple[int, int, int] | None:
        try:
            stat = self._path.stat()
        except OSError:
            return None
        return (stat.st_ino, stat.st_size, stat.st_mtime_ns)

    def get(self) -> dict[str, ModelConfig]:
        version = self._file_version()
        if version == self._observed_version:
            return self._models

        with self._lock:
            version = self._file_version()
            if version == self._observed_version:
                return self._models

            try:
                models = _load_models_from_yaml(self._path)
            except (OSError, ValueError, yaml.YAMLError):
                logger.exception(
                    "Could not reload %s; continuing with the last valid model configuration",
                    self._path,
                )
            else:
                self._models = models

            # Do not retry the same broken save on every request. A subsequent
            # file change gets a new version and triggers another attempt.
            self._observed_version = version
            return self._models


class Config:
    """Base configuration class."""

    # Environment variables
    OPENROUTER_API_KEY: ClassVar[str | None] = os.environ.get("OPENROUTER_API_KEY")

    # Database
    DATA_DIR: ClassVar[str] = os.environ.get("DATA_DIR", "data")
    DATABASE_URI: ClassVar[str] = os.environ.get("DATABASE_URI", f"sqlite:///{DATA_DIR}/dhivehi_translation_arena.db")

    # Application settings
    SECRET_KEY: ClassVar[str] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    @classmethod
    def check_configuration(cls) -> None:
        """Check for critical configuration issues."""
        if os.environ.get("FLASK_ENV") == "production" and cls.SECRET_KEY == "dev-secret-key-change-in-production":
            warnings.warn(
                "SECRET_KEY is set to default value in production! This is a security risk.",
                UserWarning,
                stacklevel=2,
            )

    MAX_MODELS_SELECTION: ClassVar[int] = int(os.environ.get("MAX_MODELS_SELECTION", "10"))

    # Glicko-2 parameters
    GLICKO_TAU: ClassVar[float] = 0.5
    GLICKO_MIN_RD: ClassVar[float] = 80.0
    GLICKO_C_PER_WEEK: ClassVar[float] = 48.6
    GLICKO_INITIAL_RD: ClassVar[float] = 350.0
    GLICKO_INITIAL_VOLATILITY: ClassVar[float] = 0.06
    DEFAULT_RATING: ClassVar[float] = 1500.0

    # Cost tiers (based on output_cost_per_mtok)
    COST_CHEAP_MAX: ClassVar[float] = 3.0
    COST_MID_MAX: ClassVar[float] = 10.0
    MAX_EXPENSIVE_GROUPS: ClassVar[int] = 2

    # Query difficulty thresholds
    DIFFICULTY_EASY_THRESHOLD: ClassVar[float] = 0.3
    DIFFICULTY_HARD_THRESHOLD: ClassVar[float] = -0.3
    DIFFICULTY_MIN_VOTES: ClassVar[int] = 3
    DIFFICULTY_MIN_MODELS: ClassVar[int] = 2

    # Stratified query selection targets per session
    STRATIFIED_TARGETS: ClassVar[dict[str, int]] = {
        "easy": 2,
        "medium": 5,
        "hard": 2,
        "unknown": 1,
    }
    STRATIFIED_TOTAL: ClassVar[int] = 10

    # Translation settings
    SYSTEM_PROMPT: ClassVar[str] = "Translate to Dhivehi. Don't explain. Only return the translated text."

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


_config_instance: Config | None = None
_models_reloader = _ModelsReloader(_resolve_models_path(), Config.MODELS)


def get_config(config_name: str | None = None) -> Config:
    """Get configuration instance (cached)."""
    global _config_instance
    if _config_instance is None:
        if config_name is None:
            config_name = os.environ.get("FLASK_ENV", "default")
        _config_instance = config.get(config_name, config["default"])()
    _config_instance.MODELS = _models_reloader.get()  # ty: ignore[invalid-attribute-access]
    return _config_instance
