"""Centralized configuration for Dhivehi Translation Arena."""

import os
import warnings
from typing import Any, ClassVar, NotRequired, TypedDict


class ModelConfig(TypedDict):
    """Configuration for a model definition."""

    name: str
    display_name: str
    type: str
    input_cost_per_mtok: float
    output_cost_per_mtok: float
    is_active: bool
    rate_limit: NotRequired[float | None]
    thinking_budget: NotRequired[int | None]
    temperature: NotRequired[float | None]
    reasoning: NotRequired[dict[str, Any]]


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
    def check_configuration(cls):
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

    # Translation settings
    SYSTEM_PROMPT: ClassVar[str] = (
        "Translate to Dhivehi. Don't explain. Only return the translated text."
    )

    # Model configurations
    MODELS: ClassVar[dict[str, ModelConfig]] = {
        "gemini-2.0-flash": {
            "name": "google/gemini-2.0-flash-001",
            "display_name": "Gemini 2.0 Flash",
            "type": "openrouter",
            "input_cost_per_mtok": 0.1,
            "output_cost_per_mtok": 0.4,
            "is_active": True,
            "rate_limit": None,
        },
        "gemini-3-pro": {
            "name": "google/gemini-3-pro-preview",
            "display_name": "Gemini 3 Pro",
            "type": "openrouter",
            "input_cost_per_mtok": 2.0,
            "output_cost_per_mtok": 12.0,
            "is_active": True,
            "rate_limit": None,
        },
        "gemini-3-pro-low": {
            "name": "google/gemini-3-pro-preview",
            "display_name": "Gemini 3 Pro (Low Reasoning)",
            "type": "openrouter",
            "input_cost_per_mtok": 2.0,
            "output_cost_per_mtok": 12.0,
            "is_active": True,
            "rate_limit": None,
            "reasoning": {"effort": "low"},
        },
        "gemini-3-pro-low-temp-0.35": {
            "name": "google/gemini-3-pro-preview",
            "display_name": "Gemini 3 Pro (Low Reasoning, Low Temp)",
            "type": "openrouter",
            "input_cost_per_mtok": 2.0,
            "output_cost_per_mtok": 12.0,
            "is_active": True,
            "rate_limit": None,
            "temperature": 0.35,
            "reasoning": {"effort": "low"},
        },
        "gemini-2.5-pro": {
            "name": "google/gemini-2.5-pro",  # Verify ID, assumption based on pattern, user asked to add it
            "display_name": "Gemini 2.5 Pro (Thinking 128)",
            "type": "openrouter",
            "input_cost_per_mtok": 1.25,
            "output_cost_per_mtok": 10.0,
            "is_active": True,
            "rate_limit": None,
            "reasoning": {
                "max_tokens": 128
            },  # "thinking budget of 128" - interpreted as max tokens for reasoning
        },
        "gemini-2.5-flash": {
            "name": "google/gemini-2.5-flash",
            "display_name": "Gemini 2.5 Flash (No Thinking)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.3,
            "output_cost_per_mtok": 2.5,
            "is_active": True,
            "rate_limit": None,
            "reasoning": {"max_tokens": 0},  # "reasoning max_tokens set to 0"
        },
        "gemini-2.5-flash-thinking": {
            "name": "google/gemini-2.5-flash",
            "display_name": "Gemini 2.5 Flash (Thinking Enabled)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.3,
            "output_cost_per_mtok": 2.5,
            "is_active": True,
            "rate_limit": None,
            "reasoning": {"enabled": True},
        },
        "gemini-2.5-flash-lite": {
            "name": "google/gemini-2.5-flash-lite",
            "display_name": "Gemini 2.5 Flash Lite",
            "type": "openrouter",
            "input_cost_per_mtok": 0.10,
            "output_cost_per_mtok": 0.40,
            "is_active": True,
            "rate_limit": None,
        },
        "claude-opus-4.5": {
            "name": "anthropic/claude-opus-4.5",
            "display_name": "Claude Opus 4.5",
            "type": "openrouter",
            "input_cost_per_mtok": 5.0,
            "output_cost_per_mtok": 25.0,
            "is_active": True,
            "rate_limit": None,
        },
        "claude-sonnet-3.7": {
            "name": "anthropic/claude-3.7-sonnet",
            "display_name": "Claude 3.7 Sonnet",
            "type": "openrouter",
            "input_cost_per_mtok": 3.0,
            "output_cost_per_mtok": 15.0,
            "is_active": True,
            "rate_limit": None,
        },
        "claude-sonnet-4": {
            "name": "anthropic/claude-sonnet-4",
            "display_name": "Claude Sonnet 4",
            "type": "openrouter",
            "input_cost_per_mtok": 3.0,
            "output_cost_per_mtok": 15.0,
            "is_active": False,
            "rate_limit": None,
        },
    }

    # API settings
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    # Functionality settings
    DEFAULT_TEMPERATURE = 0.85
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
