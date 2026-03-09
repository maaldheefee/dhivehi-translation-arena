import logging
import threading
import time
from typing import ClassVar

from openai import APITimeoutError, OpenAI

from app.config import ModelConfig, get_config

config = get_config()

logger = logging.getLogger(__name__)


class TranslationClient:
    """Base class for translation clients."""

    SYSTEM_PROMPT = config.SYSTEM_PROMPT

    # Shared state for rate limiting across instances: {model_key: {"last_request_time": float, "request_count": int}}
    _shared_state: ClassVar[dict[str, dict[str, float | int]]] = {}
    _lock = threading.Lock()

    def __init__(self, model_key: str, model_config: ModelConfig) -> None:
        """Initialize the translation client."""
        self.model_key = model_key
        self.model_name = model_config["name"]
        self.input_cost_per_mtok = model_config["input_cost_per_mtok"]
        self.output_cost_per_mtok = model_config["output_cost_per_mtok"]
        self.rate_limit = model_config.get("rate_limit")

    def translate(self, text: str) -> tuple[str, float]:
        """
        Translate the given text using the specified model.

        Args:
            text: Text to translate.

        Returns:
            Translated text and the cost of the API call.
        """
        msg = "Subclasses must implement translate()"
        raise NotImplementedError(msg)

    def _calculate_cost(self, input_tokens: float, output_tokens: float) -> float:
        """Calculate the cost of the API call."""
        cost = (
            (input_tokens * self.input_cost_per_mtok)
            + (output_tokens * self.output_cost_per_mtok)
        ) / 1_000_000
        logger.debug(
            f"Cost calculation for {self.model_name}: "
            f"input_tokens={input_tokens}, output_tokens={output_tokens}, cost={cost}"
        )
        return cost

    def _check_rate_limit(self) -> bool:
        """Check if the rate limit has been exceeded."""
        if not self.rate_limit:
            return True

        current_time = time.time()
        # Default rate limit window is 60 seconds
        rate_limit_window = 60

        with self._lock:
            # Initialize state for this model if it doesn't exist
            if self.model_key not in self._shared_state:
                self._shared_state[self.model_key] = {
                    "last_request_time": current_time,
                    "request_count": 1,
                }
                return True

            state = self._shared_state[self.model_key]
            last_request_time = state["last_request_time"]
            request_count = state["request_count"]

            if current_time - last_request_time < rate_limit_window:
                if request_count >= self.rate_limit:
                    return False
                state["request_count"] += 1
            else:
                state["last_request_time"] = current_time
                state["request_count"] = 1

        return True


class OpenRouterClient(TranslationClient):
    """Client for OpenRouter models."""

    def __init__(self, model_key: str, model_config: ModelConfig) -> None:
        """Initialize the OpenRouter client."""
        super().__init__(model_key, model_config)
        self.reasoning = model_config.get("reasoning")
        self.custom_temperature = model_config.get("temperature")
        self.timeout = model_config.get("timeout", 90.0)  # Thinking models use 180s

    def translate(self, text: str) -> tuple[str, float]:
        """Translate text using the OpenRouter API."""
        if not config.OPENROUTER_API_KEY:
            return "Error: API key not configured for OpenRouter", 0.0

        if not self._check_rate_limit():
            return (
                f"Error: Rate limit exceeded for model {self.model_name}. Please try again later.",
                0.0,
            )

        try:
            client = OpenAI(
                base_url=config.OPENROUTER_BASE_URL,
                api_key=config.OPENROUTER_API_KEY,
            )

            # Extra body parameters for reasoning models
            extra_body = {}
            if self.reasoning:
                extra_body["reasoning"] = self.reasoning

            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=self.custom_temperature
                if self.custom_temperature is not None
                else config.DEFAULT_TEMPERATURE,
                extra_body=extra_body if extra_body else None,
                timeout=self.timeout,
            )

            logger.info(
                f"Full OpenRouter Response for {self.model_name}: {completion!r}"
            )

            if not completion.choices:
                logger.warning(
                    f"OpenRouter response for {self.model_name} had no choices."
                )
                return "Error: No response generated by model.", 0.0

            choice = completion.choices[0]

            # Check for finish reason
            if choice.finish_reason == "length":
                error_msg = "Error: The response was cut off because it reached the maximum token limit."
                logger.warning(f"{error_msg} for model {self.model_name}")
                return error_msg, 0.0

            translation = choice.message.content or ""

            usage = completion.usage
            input_tokens = (
                usage.prompt_tokens
                if usage and usage.prompt_tokens is not None
                else len(text) / 4
            )
            output_tokens = (
                usage.completion_tokens
                if usage and usage.completion_tokens is not None
                else len(translation) / 4
            )

            cost = self._calculate_cost(input_tokens, output_tokens)

        except APITimeoutError:
            error_msg = f"Error: Request timed out for model {self.model_name}."
            logger.error(error_msg)
            return error_msg, 0.0

        except Exception as e:
            logger.exception(
                f"OpenRouter translation failed for {self.model_name}: {e!s}"
            )
            return f"Error: {e!s}", 0.0
        else:
            logger.info(f"OpenRouter translation successful for {self.model_name}.")
            return translation, cost


def get_translation_client(model_key: str) -> TranslationClient:
    """
    Create a translation client for the given model key.

    Args:
        model_key: The key of the model in the configuration.

    Returns:
        A translation client instance.

    Raises:
        ValueError: If the model key is unknown.
    """
    model_config = config.MODELS.get(model_key)
    if not model_config:
        msg = f"Unknown model: {model_key}"
        raise ValueError(msg)

    # All active models use OpenRouter as per requirement.
    # We use OpenRouterClient for all models since other clients have been removed.
    model_type = model_config.get("type", "openrouter")
    if model_type != "openrouter":
        logger.warning(
            f"Model {model_key} has type '{model_type}', but only 'openrouter' is supported. "
            "Using OpenRouterClient."
        )

    return OpenRouterClient(model_key, model_config)


def get_available_models() -> dict[str, str]:
    """Get a dictionary of available, active, non-hidden models."""
    return {
        key: model["display_name"]
        for key, model in config.MODELS.items()
        if model.get("is_active", True) and not model.get("is_hidden", False)
    }
