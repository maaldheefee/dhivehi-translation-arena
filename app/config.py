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
    is_hidden: NotRequired[bool]  # Hidden from UI selectors but data preserved
    rate_limit: NotRequired[float | None]
    thinking_budget: NotRequired[int | None]
    temperature: NotRequired[float | None]
    reasoning: NotRequired[dict[str, Any]]
    preset_name: NotRequired[str | None]
    base_model: NotRequired[str | None]
    timeout: NotRequired[float]  # API timeout in seconds, default 90


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
    MAX_MODELS_SELECTION: ClassVar[int] = int(
        os.environ.get("MAX_MODELS_SELECTION", "6")
    )

    # Translation settings
    SYSTEM_PROMPT: ClassVar[str] = (
        "Translate to Dhivehi. Don't explain. Only return the translated text."
    )

    # Model configurations
    # Naming convention: {base-model}[-{reasoning}]-t{temp}
    # Temperature is always explicit for stability and future-proofing
    MODELS: ClassVar[dict[str, ModelConfig]] = {
        # ==================== Gemini 2.0 Flash ====================
        "gemini-2.0-flash-t0.85": {
            "name": "google/gemini-2.0-flash-001",
            "display_name": "Gemini 2.0 Flash (T0.85)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.1,
            "output_cost_per_mtok": 0.4,
            "is_active": True,
            "rate_limit": None,
            "base_model": "Gemini 2.0 Flash",
            "temperature": 0.85,
            "preset_name": "Temp 0.85",
        },
        "gemini-2.0-flash-t0.1": {
            "name": "google/gemini-2.0-flash-001",
            "display_name": "Gemini 2.0 Flash (T0.1)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.1,
            "output_cost_per_mtok": 0.4,
            "is_active": True,
            "rate_limit": None,
            "base_model": "Gemini 2.0 Flash",
            "temperature": 0.1,
            "preset_name": "Temp 0.1",
        },
        # ==================== Gemini 3 Pro ====================
        "gemini-3-pro-t1.0": {
            "name": "google/gemini-3-pro-preview",
            "display_name": "Gemini 3 Pro (T1.0)",
            "type": "openrouter",
            "input_cost_per_mtok": 2.0,
            "output_cost_per_mtok": 12.0,
            "is_active": False,  # Disabled due to high cost
            "rate_limit": None,
            "timeout": 180.0,
            "base_model": "Gemini 3 Pro Preview",
            "temperature": 1.0,
            "preset_name": "Default, Temp 1.0",
        },
        "gemini-3-pro-low-t1.0": {
            "name": "google/gemini-3-pro-preview",
            "display_name": "Gemini 3 Pro (Low, T1.0)",
            "type": "openrouter",
            "input_cost_per_mtok": 2.0,
            "output_cost_per_mtok": 12.0,
            "is_active": True,
            "rate_limit": None,
            "reasoning": {"effort": "low"},
            "timeout": 180.0,
            "base_model": "Gemini 3 Pro Preview",
            "temperature": 1.0,
            "preset_name": "Low Reasoning, Temp 1.0",
        },
        "gemini-3-pro-low-t0.35": {
            "name": "google/gemini-3-pro-preview",
            "display_name": "Gemini 3 Pro (Low, T0.35)",
            "type": "openrouter",
            "input_cost_per_mtok": 2.0,
            "output_cost_per_mtok": 12.0,
            "is_active": True,
            "rate_limit": None,
            "temperature": 0.35,
            "reasoning": {"effort": "low"},
            "timeout": 180.0,
            "base_model": "Gemini 3 Pro Preview",
            "preset_name": "Low Reasoning, Temp 0.35",
        },
        # ==================== Gemini 3 Flash ====================
        "gemini-3-flash-t1.0": {
            "name": "google/gemini-3-flash-preview",
            "display_name": "Gemini 3 Flash (T1.0)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.5,
            "output_cost_per_mtok": 3.0,
            "is_active": True,
            "rate_limit": None,
            "timeout": 180.0,
            "base_model": "Gemini 3 Flash Preview",
            "temperature": 1.0,
            "preset_name": "Default, Temp 1.0",
        },
        "gemini-3-flash-low-t1.0": {
            "name": "google/gemini-3-flash-preview",
            "display_name": "Gemini 3 Flash (Low, T1.0)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.5,
            "output_cost_per_mtok": 3.0,
            "is_active": True,
            "rate_limit": None,
            "reasoning": {"effort": "minimal"},
            "timeout": 180.0,
            "base_model": "Gemini 3 Flash Preview",
            "temperature": 1.0,
            "preset_name": "Min Reasoning, Temp 1.0",
        },
        "gemini-3-flash-t0.3": {
            "name": "google/gemini-3-flash-preview",
            "display_name": "Gemini 3 Flash (T0.3)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.5,
            "output_cost_per_mtok": 3.0,
            "is_active": True,
            "rate_limit": None,
            "timeout": 180.0,
            "base_model": "Gemini 3 Flash Preview",
            "temperature": 0.3,
            "preset_name": "Temp 0.3",
        },
        "gemini-3-flash-low-t0.3": {
            "name": "google/gemini-3-flash-preview",
            "display_name": "Gemini 3 Flash (Low, T0.3)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.5,
            "output_cost_per_mtok": 3.0,
            "is_active": True,
            "rate_limit": None,
            "reasoning": {"effort": "minimal"},
            "timeout": 180.0,
            "base_model": "Gemini 3 Flash Preview",
            "temperature": 0.3,
            "preset_name": "Min Reasoning, Temp 0.3",
        },
        # ==================== Gemini 2.5 Pro ====================
        "gemini-2.5-pro-min-t0.85": {
            "name": "google/gemini-2.5-pro",
            "display_name": "Gemini 2.5 Pro (Min, T0.85)",
            "type": "openrouter",
            "input_cost_per_mtok": 1.25,
            "output_cost_per_mtok": 10.0,
            "is_active": False,
            "rate_limit": None,
            "reasoning": {"max_tokens": 128},
            "timeout": 180.0,
            "base_model": "Gemini 2.5 Pro",
            "temperature": 0.85,
            "preset_name": "Min Thinking, Temp 0.85",
        },
        "gemini-2.5-pro-min-t0.1": {
            "name": "google/gemini-2.5-pro",
            "display_name": "Gemini 2.5 Pro (Min, T0.1)",
            "type": "openrouter",
            "input_cost_per_mtok": 1.25,
            "output_cost_per_mtok": 10.0,
            "is_active": True,
            "rate_limit": None,
            "reasoning": {"max_tokens": 128},
            "timeout": 180.0,
            "base_model": "Gemini 2.5 Pro",
            "temperature": 0.1,
            "preset_name": "Min Thinking, Temp 0.1",
        },
        # ==================== Gemini 2.5 Flash ====================
        "gemini-2.5-flash-t0.85": {
            "name": "google/gemini-2.5-flash",
            "display_name": "Gemini 2.5 Flash (T0.85)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.3,
            "output_cost_per_mtok": 2.5,
            "is_active": True,
            "rate_limit": None,
            "reasoning": {"max_tokens": 0},
            "base_model": "Gemini 2.5 Flash",
            "temperature": 0.85,
            "preset_name": "No Thinking, Temp 0.85",
        },
        "gemini-2.5-flash-t0.1": {
            "name": "google/gemini-2.5-flash",
            "display_name": "Gemini 2.5 Flash (T0.1)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.3,
            "output_cost_per_mtok": 2.5,
            "is_active": True,
            "rate_limit": None,
            "reasoning": {"max_tokens": 0},
            "base_model": "Gemini 2.5 Flash",
            "temperature": 0.1,
            "preset_name": "No Thinking, Temp 0.1",
        },
        "gemini-2.5-flash-reasoning-t0.85": {
            "name": "google/gemini-2.5-flash",
            "display_name": "Gemini 2.5 Flash (Reasoning, T0.85)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.3,
            "output_cost_per_mtok": 2.5,
            "is_active": True,
            "rate_limit": None,
            "reasoning": {"enabled": True},
            "timeout": 180.0,
            "base_model": "Gemini 2.5 Flash",
            "temperature": 0.85,
            "preset_name": "Reasoning, Temp 0.85",
        },
        # ==================== Gemini 2.5 Flash Lite ====================
        "gemini-2.5-flash-lite-t0.85": {
            "name": "google/gemini-2.5-flash-lite",
            "display_name": "Gemini 2.5 Flash Lite (T0.85)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.10,
            "output_cost_per_mtok": 0.40,
            "is_active": False,
            "rate_limit": None,
            "base_model": "Gemini 2.5 Flash Lite",
            "temperature": 0.85,
            "preset_name": "Temp 0.85",
        },
        "gemini-2.5-flash-lite-t0.1": {
            "name": "google/gemini-2.5-flash-lite",
            "display_name": "Gemini 2.5 Flash Lite (T0.1)",
            "type": "openrouter",
            "input_cost_per_mtok": 0.10,
            "output_cost_per_mtok": 0.40,
            "is_active": False,
            "rate_limit": None,
            "base_model": "Gemini 2.5 Flash Lite",
            "temperature": 0.1,
            "preset_name": "Temp 0.1",
        },
        # ==================== Claude Opus 4.5 ====================
        "claude-opus-4.5-t0.85": {
            "name": "anthropic/claude-opus-4.5",
            "display_name": "Claude Opus 4.5 (T0.85)",
            "type": "openrouter",
            "input_cost_per_mtok": 5.0,
            "output_cost_per_mtok": 25.0,
            "is_active": False,
            "rate_limit": None,
            "base_model": "Claude Opus 4.5",
            "temperature": 0.85,
            "preset_name": "Temp 0.85",
        },
        "claude-opus-4.5-t0.1": {
            "name": "anthropic/claude-opus-4.5",
            "display_name": "Claude Opus 4.5 (T0.1)",
            "type": "openrouter",
            "input_cost_per_mtok": 5.0,
            "output_cost_per_mtok": 25.0,
            "is_active": True,
            "rate_limit": None,
            "base_model": "Claude Opus 4.5",
            "temperature": 0.1,
            "preset_name": "Temp 0.1",
        },
        # ==================== Claude 3.7 Sonnet ====================
        "claude-sonnet-3.7-t0.85": {
            "name": "anthropic/claude-3.7-sonnet",
            "display_name": "Claude 3.7 Sonnet (T0.85)",
            "type": "openrouter",
            "input_cost_per_mtok": 3.0,
            "output_cost_per_mtok": 15.0,
            "is_active": False,
            "rate_limit": None,
            "base_model": "Claude 3.7 Sonnet",
            "temperature": 0.85,
            "preset_name": "Temp 0.85",
        },
        "claude-sonnet-3.7-t0.1": {
            "name": "anthropic/claude-3.7-sonnet",
            "display_name": "Claude 3.7 Sonnet (T0.1)",
            "type": "openrouter",
            "input_cost_per_mtok": 3.0,
            "output_cost_per_mtok": 15.0,
            "is_active": True,
            "rate_limit": None,
            "base_model": "Claude 3.7 Sonnet",
            "temperature": 0.1,
            "preset_name": "Temp 0.1",
        },
        # ==================== Claude 3.5 Sonnet ====================
        "claude-sonnet-3.5-t0.85": {
            "name": "anthropic/claude-3.5-sonnet",
            "display_name": "Claude 3.5 Sonnet (T0.85)",
            "type": "openrouter",
            "input_cost_per_mtok": 3.0,
            "output_cost_per_mtok": 15.0,
            "is_active": True,
            "rate_limit": None,
            "base_model": "Claude 3.5 Sonnet",
            "temperature": 0.85,
            "preset_name": "Temp 0.85",
        },
        "claude-sonnet-3.5-t0.1": {
            "name": "anthropic/claude-3.5-sonnet",
            "display_name": "Claude 3.5 Sonnet (T0.1)",
            "type": "openrouter",
            "input_cost_per_mtok": 3.0,
            "output_cost_per_mtok": 15.0,
            "is_active": True,
            "rate_limit": None,
            "base_model": "Claude 3.5 Sonnet",
            "temperature": 0.1,
            "preset_name": "Temp 0.1",
        },
        # ==================== Claude Sonnet 4 ====================
        "claude-sonnet-4-t0.85": {
            "name": "anthropic/claude-sonnet-4",
            "display_name": "Claude Sonnet 4 (T0.85)",
            "type": "openrouter",
            "input_cost_per_mtok": 3.0,
            "output_cost_per_mtok": 15.0,
            "is_active": False,
            "rate_limit": None,
            "base_model": "Claude Sonnet 4",
            "temperature": 0.85,
            "preset_name": "Temp 0.85",
        },
        "claude-sonnet-4-t0.1": {
            "name": "anthropic/claude-sonnet-4",
            "display_name": "Claude Sonnet 4 (T0.1)",
            "type": "openrouter",
            "input_cost_per_mtok": 3.0,
            "output_cost_per_mtok": 15.0,
            "is_active": False,
            "rate_limit": None,
            "base_model": "Claude Sonnet 4",
            "temperature": 0.1,
            "preset_name": "Temp 0.1",
        },
    }

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
