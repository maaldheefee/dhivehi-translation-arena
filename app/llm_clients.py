import os
import time

from google import genai
from google.genai import types
from openai import OpenAI

# Initialize Google Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)


class TranslationClient:
    """Base class for translation clients"""

    SYSTEM_PROMPT = (
        "Translate to Dhivehi. Don't explain. Only return the translated text."
    )

    def translate(self, text: str) -> tuple[str, float]:
        """
        Translate the given text using the specified model

        Args:
            text (str): Text to translate

        Returns:
            Tuple[str, float]: Translated text and the cost of the API call
        """
        msg = "Subclasses must implement translate()"
        raise NotImplementedError(msg)


class GeminiClient(TranslationClient):
    """Base client for Gemini models"""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.last_request_time = None
        self.request_count = 0
        self.input_cost_per_mtok = None
        self.output_cost_per_mtok = None

    def _check_rate_limit(self) -> bool:
        if self.model_name == "gemini-2.0-pro-exp-02-05":
            current_time = time.time()
            if self.last_request_time and current_time - self.last_request_time < 60:
                if self.request_count >= 5:
                    return False
                self.request_count += 1
            else:
                self.last_request_time = current_time
                self.request_count = 1
        return True

    def translate(self, text: str) -> tuple[str, float]:
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            return "API key not configured for Gemini", 0.0

        if not self._check_rate_limit():
            return "Rate limit exceeded. Please wait a minute before trying again.", 0.0

        try:
            client = genai.Client(api_key=gemini_api_key)

            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=text),
                    ],
                ),
            ]

            generate_content_config = types.GenerateContentConfig(
                temperature=0.85,
                max_output_tokens=2048,
                response_mime_type="text/plain",
                system_instruction=[types.Part.from_text(text=self.SYSTEM_PROMPT)],
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=generate_content_config,
            )

            response_text = response.text
            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count
            cost = self._calculate_cost(input_tokens, output_tokens)

            return response_text, cost

        except Exception as e:
            return f"Error: {e!s}", 0.0

    def _calculate_cost(self, input_tokens: float, output_tokens: float) -> float:
        return (input_tokens * self.input_cost_per_mtok / 1_000_000) + (
            output_tokens * self.output_cost_per_mtok / 1_000_000
        )


class GeminiFlashClient(GeminiClient):
    """Client for Gemini 2.0 Flash"""

    def __init__(self):
        super().__init__("gemini-2.0-flash")
        self.input_cost_per_mtok = 0.25
        self.output_cost_per_mtok = 0.75


class GeminiProClient(GeminiClient):
    """Client for Gemini 2.0 Pro Experimental"""

    def __init__(self):
        super().__init__("gemini-2.0-pro-exp-02-05")
        self.input_cost_per_mtok = 0
        self.output_cost_per_mtok = 0


class SonnetClient(TranslationClient):
    """Client for Sonnet 3.7 via OpenRoute API"""

    def translate(self, text: str) -> tuple[str, float]:
        openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            return "API key not configured for OpenRouter", 0.0

        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key,
            )

            completion = client.chat.completions.create(
                model="anthropic/claude-3.7-sonnet",
                messages=[
                    {
                        "role": "system",
                        "content": self.SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0.7,
            )

            translation = completion.choices[0].message.content

            input_tokens = (
                completion.usage.prompt_tokens
                if hasattr(completion, "usage")
                and hasattr(completion.usage, "prompt_tokens")
                else len(text) / 4
            )
            output_tokens = (
                completion.usage.completion_tokens
                if hasattr(completion, "usage")
                and hasattr(completion.usage, "completion_tokens")
                else len(translation) / 4
            )

            # $0.003 / 1K input tokens, $0.015 / 1K output tokens
            cost = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)

        except Exception as e:
            return f"Error: {e!s}", 0.0
        else:
            return translation, cost


# Factory to get the appropriate client
def get_translation_client(model_name: str) -> TranslationClient:
    """
    Factory function to get the appropriate translation client

    Args:
        model_name (str): Name of the model to use

    Returns:
        TranslationClient: The appropriate client for the specified model
    """
    if model_name == "gemini-flash":
        return GeminiFlashClient()
    if model_name == "gemini-pro":
        return GeminiProClient()
    if model_name == "sonnet":
        return SonnetClient()
    msg = f"Unknown model: {model_name}"
    raise ValueError(msg)
