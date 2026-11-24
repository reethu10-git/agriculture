"""
AGRI-2: Company Nexus AI API Client
Integrates with the company's Nexus API (OpenAI-compatible) endpoint.
Provides safe credential handling, connection timeout management, rate-limit retries,
and robust error reporting.
"""

import os
from typing import Dict, Any, List, Optional
import openai
from config.settings import NEXUS_API_KEY, NEXUS_BASE_URL, NEXUS_MODEL


class NexusClient:
    """Client for Nexus AI OpenAI-compatible completions API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 15.0
    ):
        if api_key is None:
            raw_key = os.getenv("NEXUS_API_KEY", NEXUS_API_KEY)
        else:
            raw_key = api_key
        self.api_key = raw_key.strip() if isinstance(raw_key, str) else ""

        if base_url is None:
            raw_url = os.getenv("NEXUS_BASE_URL", NEXUS_BASE_URL)
        else:
            raw_url = base_url
        self.base_url = raw_url.strip() if isinstance(raw_url, str) else ""

        if model is None:
            raw_model = os.getenv("NEXUS_MODEL", NEXUS_MODEL)
        else:
            raw_model = model
        self.model = raw_model.strip() if isinstance(raw_model, str) else ""

        self.timeout = timeout

        self.client: Optional[openai.OpenAI] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initializes OpenAI client if valid API key and base URL are present."""
        has_valid_key = bool(
            self.api_key
            and self.api_key.strip()
            and self.api_key.strip() != "your_nexus_api_key_here"
        )
        has_valid_url = bool(
            self.base_url
            and self.base_url.strip()
        )
        if has_valid_key and has_valid_url:
            try:
                self.client = openai.OpenAI(
                    api_key=self.api_key.strip(),
                    base_url=self.base_url.strip(),
                    timeout=self.timeout,
                    max_retries=1
                )
            except Exception:
                self.client = None
        else:
            self.client = None

    def is_configured(self) -> bool:
        """Returns True if valid API credentials and base URL appear to be configured."""
        has_valid_key = bool(
            self.api_key
            and self.api_key.strip()
            and self.api_key.strip() != "your_nexus_api_key_here"
        )
        has_valid_url = bool(
            self.base_url
            and self.base_url.strip()
        )
        return bool(has_valid_key and has_valid_url and self.client is not None)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1200
    ) -> Dict[str, Any]:
        """
        Submits chat completion request to Nexus API with comprehensive error handling.

        Returns:
            dict: {"success": bool, "content": str, "error_type": str, "error_message": str}
        """
        if not self.is_configured():
            return {
                "success": False,
                "content": "",
                "error_type": "MISSING_API_KEY",
                "error_message": "Nexus API key is not configured or contains default placeholder. Please set NEXUS_API_KEY in .env."
            }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content or ""
            return {
                "success": True,
                "content": content.strip(),
                "error_type": None,
                "error_message": None,
                "model_used": self.model
            }

        except openai.AuthenticationError as e:
            return {
                "success": False,
                "content": "",
                "error_type": "AUTHENTICATION_FAILED",
                "error_message": f"Nexus API authentication failed: Check that NEXUS_API_KEY is valid. ({str(e)})"
            }
        except openai.RateLimitError as e:
            return {
                "success": False,
                "content": "",
                "error_type": "RATE_LIMIT_EXCEEDED",
                "error_message": f"Nexus API rate limit reached. Please wait a moment before retrying. ({str(e)})"
            }
        except openai.APITimeoutError as e:
            return {
                "success": False,
                "content": "",
                "error_type": "TIMEOUT",
                "error_message": f"Nexus API request timed out after {self.timeout} seconds. ({str(e)})"
            }
        except openai.APIConnectionError as e:
            return {
                "success": False,
                "content": "",
                "error_type": "CONNECTION_ERROR",
                "error_message": f"Could not connect to Nexus API at {self.base_url}. Verify network connectivity. ({str(e)})"
            }
        except Exception as e:
            return {
                "success": False,
                "content": "",
                "error_type": "GENERAL_API_ERROR",
                "error_message": f"Unexpected Nexus API error: {str(e)}"
            }
