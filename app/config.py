"""Centralized configuration for Dhivehi Translation Arena."""

import os
from typing import ClassVar, NotRequired, TypedDict


class ModelConfig(TypedDict):
    """Configuration for a model definition."""

    name: str
    display_name: str
    type: str
    input_cost_per_mtok: float
    output_cost_per_mtok: float
    rate_limit: NotRequired[float | None]
    thinking_budget: NotRequired[int | None]


class Config:
    """Base configuration class."""

    # Environment variables
    GEMINI_API_KEY: ClassVar[str | None] = os.environ.get("GEMINI_API_KEY")
    OPENROUTER_API_KEY: ClassVar[str | None] = os.environ.get("OPENROUTER_API_KEY")

    # Database
    DATABASE_URI: ClassVar[str] = os.environ.get(
        "DATABASE_URI", "sqlite:///dhivehi_translation_arena.db"
    )

    # Application settings
    SECRET_KEY: ClassVar[str] = os.environ.get(
        "SECRET_KEY", "dev-secret-key-change-in-production"
    )
    MAX_CACHE_SIZE: ClassVar[int] = int(os.environ.get("MAX_CACHE_SIZE", "100"))

    # Translation settings
    SYSTEM_PROMPT: ClassVar[str] = (
        "Translate to Dhivehi. Don't explain. Only return the translated text."
    )

    # Model configurations
    MODELS: ClassVar[dict[str, ModelConfig]] = {
        "gemini-2.0-flash": {
            "name": "gemini-2.0-flash",
            "display_name": "Gemini 2.0 Flash",
            "type": "gemini",
            "input_cost_per_mtok": 0.1,
            "output_cost_per_mtok": 0.4,
            "rate_limit": None,
        },
        "gemini-2.5-pro": {
            "name": "gemini-2.5-pro",
            "display_name": "Gemini 2.5 Pro",
            "type": "gemini",
            "input_cost_per_mtok": 1.25,
            "output_cost_per_mtok": 10.00,
            "rate_limit": None,
        },
        "gemini-2.5-flash": {
            "name": "gemini-2.5-flash",
            "display_name": "Gemini 2.5 Flash",
            "type": "gemini",
            "input_cost_per_mtok": 0.2,
            "output_cost_per_mtok": 2.5,
            "rate_limit": None,
            "thinking_budget": 0,
        },
        "gemini-2.5-flash-lite": {
            "name": "gemini-2.5-flash-lite-preview-06-17",
            "display_name": "Gemini 2.5 Flash Lite Preview",
            "type": "gemini",
            "input_cost_per_mtok": 0.1,
            "output_cost_per_mtok": 0.4,
            "rate_limit": None,
            "thinking_budget": 0,
        },
        "claude-sonnet-3.7": {
            "name": "anthropic/claude-3.7-sonnet",
            "display_name": "Claude 3.7 Sonnet",
            "type": "openrouter",
            "input_cost_per_mtok": 3.0,
            "output_cost_per_mtok": 15.0,
            "rate_limit": None,
        },
        "claude-sonnet-4": {
            "name": "anthropic/claude-sonnet-4",
            "display_name": "Claude Sonnet 4",
            "type": "openrouter",
            "input_cost_per_mtok": 3.0,
            "output_cost_per_mtok": 15.0,
            "rate_limit": None,
        },
    }

    # API settings
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    # Model settings
    DEFAULT_TEMPERATURE = 0.85
    MAX_OUTPUT_TOKENS = 2048

    # Rate limiting
    GEMINI_PRO_RATE_LIMIT = 5  # requests per minute
    GEMINI_PRO_RATE_WINDOW = 60  # seconds


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
