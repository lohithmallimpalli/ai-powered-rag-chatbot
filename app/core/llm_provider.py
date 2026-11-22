
import logging
from typing import List, Dict, Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Custom exception for LLM provider errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        provider: str = "unknown"
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.provider = provider


class UnifiedLLMProvider:
    """
    Unified LLM interface supporting Google Gemini and OpenAI.
    Uses the current Google Gen AI SDK.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.gemini_model = settings.GEMINI_MODEL
        self.openai_model = settings.OPENAI_MODEL

    def update_credentials(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """Update provider credentials at runtime."""

        if provider:
            self.provider = provider.lower()
            settings.LLM_PROVIDER = self.provider

        if api_key:
            if self.provider == "openai":
                settings.OPENAI_API_KEY = api_key
            else:
                settings.GEMINI_API_KEY = api_key

        if model:
            if self.provider == "openai":
                self.openai_model = model
                settings.OPENAI_MODEL = model
            else:
                self.gemini_model = model
                settings.GEMINI_MODEL = model

    def get_active_provider_info(self) -> Dict[str, Any]:
        has_key = settings.is_api_key_configured()

        current_model = (
            self.openai_model
            if self.provider == "openai"
            else self.gemini_model
        )

        return {
            "provider": self.provider,
            "model": current_model,
            "api_key_configured": has_key
        }

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.2
    ) -> str:

        if self.provider == "openai":
            return self._generate_openai(
                system_prompt,
                user_prompt,
                conversation_history,
                temperature
            )

        return self._generate_gemini(
            system_prompt,
            user_prompt,
            conversation_history,
            temperature
        )

    def _generate_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.2
    ) -> str:

        api_key = settings.GEMINI_API_KEY

        if not api_key or api_key.startswith("your_"):
            raise LLMProviderError(
                "Gemini API key is not configured. Please check Settings.",
                status_code=401,
                provider="gemini"
            )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            contents = []

            if conversation_history:
                for msg in conversation_history:
                    role = (
                        "user"
                        if msg.get("role") == "user"
                        else "model"
                    )

                    content = msg.get("content", "")

                    if content:
                        contents.append(
                            types.Content(
                                role=role,
                                parts=[
                                    types.Part.from_text(text=content)
                                ]
                            )
                        )

            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=user_prompt)
                    ]
                )
            )

            response = client.models.generate_content(
                model=self.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=2048
                )
            )

            answer = response.text

            if not answer:
                raise LLMProviderError(
                    "Gemini returned an empty response.",
                    status_code=502,
                    provider="gemini"
                )

            return answer

        except LLMProviderError:
            raise

        except Exception as e:
            err_msg = str(e)
            lower_error = err_msg.lower()

            logger.exception("Gemini API Error")

            if (
                "api_key_invalid" in lower_error
                or "invalid api key" in lower_error
                or "permission denied" in lower_error
            ):
                raise LLMProviderError(
                    "Invalid or unauthorized Gemini API key. "
                    "Please check your API key in Render Settings.",
                    status_code=401,
                    provider="gemini"
                )

            if (
                "resource_exhausted" in lower_error
                or "quota" in lower_error
                or "429" in lower_error
            ):
                raise LLMProviderError(
                    "Gemini API quota or rate limit exceeded. "
                    "Please try again later.",
                    status_code=429,
                    provider="gemini"
                )

            if (
                "not found" in lower_error
                or "404" in lower_error
                or "not supported" in lower_error
            ):
                raise LLMProviderError(
                    f"Gemini model '{self.gemini_model}' is unavailable. "
                    "Please check the model name and API access.",
                    status_code=404,
                    provider="gemini"
                )

            raise LLMProviderError(
                f"Gemini API Error: {err_msg}",
                status_code=500,
                provider="gemini"
            )

    def _generate_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.2
    ) -> str:

        api_key = settings.OPENAI_API_KEY

        if not api_key or api_key.startswith("your_"):
            raise LLMProviderError(
                "OpenAI API key is not configured. Please check Settings.",
                status_code=401,
                provider="openai"
            )

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key,
                timeout=120.0
            )

            messages = [
                {"role": "system", "content": system_prompt}
            ]

            if conversation_history:
                for msg in conversation_history:
                    role = (
                        "user"
                        if msg.get("role") == "user"
                        else "assistant"
                    )

                    messages.append({
                        "role": role,
                        "content": msg.get("content", "")
                    })

            messages.append({
                "role": "user",
                "content": user_prompt
            })

            response = client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                temperature=temperature,
                max_tokens=2048
            )

            answer = response.choices[0].message.content

            if not answer:
                raise LLMProviderError(
                    "OpenAI returned an empty response.",
                    status_code=502,
                    provider="openai"
                )

            return answer

        except LLMProviderError:
            raise

        except Exception as e:
            err_msg = str(e)
            lower_error = err_msg.lower()

            logger.exception("OpenAI API Error")

            if (
                "incorrect api key" in lower_error
                or "invalid_api_key" in lower_error
            ):
                raise LLMProviderError(
                    "Invalid OpenAI API key.",
                    status_code=401,
                    provider="openai"
                )

            if (
                "rate limit" in lower_error
                or "insufficient_quota" in lower_error
            ):
                raise LLMProviderError(
                    "OpenAI rate limit or quota exceeded.",
                    status_code=429,
                    provider="openai"
                )

            raise LLMProviderError(
                f"OpenAI API Error: {err_msg}",
                status_code=500,
                provider="openai"
            )


# Global singleton
llm_provider = UnifiedLLMProvider()
