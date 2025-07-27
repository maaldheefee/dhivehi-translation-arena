# M-2: app/llm_clients.py
import logging
import time
from typing import Any

from google import genai
from google.genai import types
from openai import OpenAI

from app.config import get_config

config = get_config()

logger = logging.getLogger(__name__)


class TranslationClient:
    """Base class for translation clients."""

    SYSTEM_PROMPT = config.SYSTEM_PROMPT

    def __init__(self, model_config: dict[str, Any]):
        """Initialize the translation client."""
        self.model_name = model_config["name"]
        self.input_cost_per_mtok = model_config["input_cost_per_mtok"]
        self.output_cost_per_mtok = model_config["output_cost_per_mtok"]
        self.rate_limit = model_config.get("rate_limit")
        self.last_request_time = 0.0
        self.request_count = 0

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
        if current_time - self.last_request_time < config.GEMINI_PRO_RATE_WINDOW:
            if self.request_count >= self.rate_limit:
                return False
            self.request_count += 1
        else:
            self.last_request_time = current_time
            self.request_count = 1
        return True


class GeminiClient(TranslationClient):
    """Client for Gemini models."""

    def __init__(self, model_config: dict[str, Any]):
        """Initialize the Gemini client."""
        super().__init__(model_config)
        self.thinking_budget = model_config.get("thinking_budget")

    def translate(self, text: str) -> tuple[str, float]:
        """Translate text using the Gemini API."""
        if not config.GEMINI_API_KEY:
            return "API key not configured for Gemini", 0.0

        if not self._check_rate_limit():
            return "Rate limit exceeded. Please wait a minute before trying again.", 0.0

        try:
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=text),
                    ],
                ),
            ]

            gen_config_params = {
                "temperature": config.DEFAULT_TEMPERATURE,
                "max_output_tokens": config.MAX_OUTPUT_TOKENS,
                "response_mime_type": "text/plain",
            }

            if self.thinking_budget is not None:
                gen_config_params["thinking_config"] = types.ThinkingConfig(
                    thinking_budget=self.thinking_budget
                )

            generation_config = types.GenerateContentConfig(**gen_config_params)
            system_instruction = types.Part.from_text(text=self.SYSTEM_PROMPT)

            generation_config.system_instruction = [system_instruction]

            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=generation_config,
            )

            logger.info(f"Full Gemini Response for {self.model_name}: {response!r}")

            if (
                hasattr(response, "prompt_feedback")
                and response.prompt_feedback
                and response.prompt_feedback.block_reason
            ):
                reason = response.prompt_feedback.block_reason.name
                error_msg = (
                    f"Error: Translation blocked by API for safety reasons: {reason}"
                )
                logger.warning(error_msg)
                return error_msg, 0.0

            # --- Start of Fix ---
            # Check for MAX_TOKENS finish reason, which also results in an empty response.
            if (
                response.candidates
                and response.candidates[0].finish_reason
                == types.FinishReason.MAX_TOKENS
            ):
                error_msg = "Error: The response was cut off because it reached the maximum token limit."
                logger.warning(f"{error_msg} for model {self.model_name}")
                return error_msg, 0.0
            # --- End of Fix ---

            response_text = response.text
            if not response_text:
                logger.warning(
                    f"Gemini response for {self.model_name} was successful but empty."
                )
                return "Error: No response generated by model.", 0.0

            input_tokens = 0
            output_tokens = 0
            if response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0

            cost = self._calculate_cost(input_tokens, output_tokens)

            logger.info(f"Gemini translation successful for {self.model_name}.")
            return str(response_text), float(cost)

        except Exception as e:
            logger.exception(f"Gemini translation failed for {self.model_name}")
            return f"Error: An exception occurred - {e!s}", 0.0


class OpenRouterClient(TranslationClient):
    """Client for OpenRouter models."""

    def translate(self, text: str) -> tuple[str, float]:
        """Translate text using the OpenRouter API."""
        if not config.OPENROUTER_API_KEY:
            return "API key not configured for OpenRouter", 0.0

        try:
            client = OpenAI(
                base_url=config.OPENROUTER_BASE_URL,
                api_key=config.OPENROUTER_API_KEY,
            )

            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=config.DEFAULT_TEMPERATURE,
            )

            logger.info(
                f"Full OpenRouter Response for {self.model_name}: {completion!r}"
            )

            if not completion.choices:
                logger.warning(
                    f"OpenRouter response for {self.model_name} had no choices."
                )
                return "Error: No response generated by model.", 0.0

            translation = completion.choices[0].message.content or ""

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
        ValueError: If the model key or type is unknown.
    """
    model_config = config.MODELS.get(model_key)
    if not model_config:
        msg = f"Unknown model: {model_key}"
        raise ValueError(msg)

    model_type = model_config.get("type")
    if model_type == "gemini":
        return GeminiClient(model_config)
    if model_type == "openrouter":
        return OpenRouterClient(model_config)

    msg = f"Unsupported model type: {model_type}"
    raise ValueError(msg)


def get_available_models() -> dict[str, str]:
    """Get a dictionary of available, active models."""
    return {
        key: model["display_name"]
        for key, model in config.MODELS.items()
        if model.get("is_active", True)
    }
