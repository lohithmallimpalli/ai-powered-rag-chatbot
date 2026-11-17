import logging
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class LLMProviderError(Exception):
    """Custom exception for LLM provider errors."""
    def __init__(self, message: str, status_code: int = 500, provider: str = "unknown"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.provider = provider

class UnifiedLLMProvider:
    """
    Unified LLM interface supporting both Google Gemini and OpenAI
    with robust error handling, rate-limit defense, and dynamic provider switching.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.gemini_model = settings.GEMINI_MODEL
        self.openai_model = settings.OPENAI_MODEL

    def update_credentials(self, provider: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        """Allows updating provider credentials at runtime."""
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
        current_model = self.openai_model if self.provider == "openai" else self.gemini_model
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
        """
        Dispatches generation to the active provider (Gemini or OpenAI).
        """
        if self.provider == "openai":
            return self._generate_openai(system_prompt, user_prompt, conversation_history, temperature)
        else:
            return self._generate_gemini(system_prompt, user_prompt, conversation_history, temperature)

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
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file or via Settings.",
                status_code=401,
                provider="gemini"
            )

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)

            # Build generation config
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=2048,
            )

            # Initialize model with system instruction
            model = genai.GenerativeModel(
                model_name=self.gemini_model,
                system_instruction=system_prompt,
                generation_config=generation_config
            )

            # Build chat history if available
            chat_contents = []
            if conversation_history:
                for msg in conversation_history:
                    role = "user" if msg.get("role") == "user" else "model"
                    chat_contents.append({
                        "role": role,
                        "parts": [msg.get("content", "")]
                    })

            # Add current user prompt
            chat_contents.append({
                "role": "user",
                "parts": [user_prompt]
            })

            response = model.generate_content(chat_contents)
            
            if not response.text:
                raise LLMProviderError("Empty response received from Gemini model.", status_code=502, provider="gemini")
                
            return response.text

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Gemini API Error: {err_msg}")
            
            if "API_KEY_INVALID" in err_msg or "invalid api key" in err_msg.lower():
                raise LLMProviderError(
                    "Invalid Google Gemini API Key. Please verify your GEMINI_API_KEY in the .env file.",
                    status_code=401,
                    provider="gemini"
                )
            elif "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
                raise LLMProviderError(
                    "Google Gemini API quota exceeded or rate limit hit. Please retry in a few moments.",
                    status_code=429,
                    provider="gemini"
                )
            elif "not found" in err_msg.lower() or "404" in err_msg:
                # Attempt fallback to gemini-1.5-flash if specified model is unavailable
                raise LLMProviderError(
                    f"Gemini model '{self.gemini_model}' not found or unavailable. Please check the model name.",
                    status_code=404,
                    provider="gemini"
                )
            else:
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
                "OpenAI API key is not configured. Please set OPENAI_API_KEY in your .env file or via Settings.",
                status_code=401,
                provider="openai"
            )

        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, timeout=30.0)

            messages = [{"role": "system", "content": system_prompt}]
            
            if conversation_history:
                for msg in conversation_history:
                    role = "user" if msg.get("role") == "user" else "assistant"
                    messages.append({"role": role, "content": msg.get("content", "")})

            messages.append({"role": "user", "content": user_prompt})

            response = client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                temperature=temperature,
                max_tokens=2048
            )

            content = response.choices[0].message.content
            if not content:
                raise LLMProviderError("Empty response received from OpenAI.", status_code=502, provider="openai")
                
            return content

        except Exception as e:
            err_msg = str(e)
            logger.error(f"OpenAI API Error: {err_msg}")
            
            if "Incorrect API key" in err_msg or "invalid_api_key" in err_msg.lower():
                raise LLMProviderError(
                    "Invalid OpenAI API Key. Please verify your OPENAI_API_KEY in .env.",
                    status_code=401,
                    provider="openai"
                )
            elif "rate limit" in err_msg.lower() or "insufficient_quota" in err_msg.lower():
                raise LLMProviderError(
                    "OpenAI rate limit or quota exceeded. Please check your OpenAI account billing.",
                    status_code=429,
                    provider="openai"
                )
            else:
                raise LLMProviderError(
                    f"OpenAI API Error: {err_msg}",
                    status_code=500,
                    provider="openai"
                )

# Global singleton
llm_provider = UnifiedLLMProvider()
