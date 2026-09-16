"""Configurable LLM Client for VeriRAG Evaluation Judges.

Supports OpenAI, Gemini, Anthropic, or OpenAI-compatible local endpoints (e.g. Ollama, vLLM).
Uses httpx directly without requiring heavy vendor SDKs.
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("verirag.llm_client")


class LLMClient:
    """Configurable HTTP client for external LLM judge execution."""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "").strip().lower()
        self.model = os.getenv("LLM_MODEL", "").strip()
        self.api_key = (
            os.getenv("API_KEY", "").strip()
            or os.getenv("OPENAI_API_KEY", "").strip()
            or os.getenv("GEMINI_API_KEY", "").strip()
            or os.getenv("ANTHROPIC_API_KEY", "").strip()
        )
        self.api_base = os.getenv("LLM_API_BASE", "").strip()

    def is_configured(self) -> bool:
        """Return True if an external LLM provider is explicitly enabled and configured."""
        if not self.provider or self.provider in ("local", "none", "deterministic", "offline"):
            return False
        return True

    def validate_configuration(self) -> None:
        """Validate LLM configuration and raise friendly error if misconfigured."""
        if self.is_configured() and not self.api_key and not self.provider.startswith("ollama"):
            raise ValueError(
                f"LLM provider '{self.provider}' is configured in .env, but no valid API key was provided. "
                f"Please set API_KEY (or {self.provider.upper()}_API_KEY) in your .env configuration, "
                f"or set LLM_PROVIDER=local to use the built-in local semantic evaluation engine."
            )

    def generate_json(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Call external LLM API expecting a JSON structured response.

        Returns parsed dictionary, or None if external LLM is not configured.
        """
        if not self.is_configured():
            return None

        self.validate_configuration()

        try:
            if self.provider in ("openai", "azure", "groq", "together", "ollama", "vllm"):
                return self._call_openai_compatible(system_prompt, user_prompt)
            elif self.provider in ("gemini", "google"):
                return self._call_gemini(system_prompt, user_prompt)
            elif self.provider == "anthropic":
                return self._call_anthropic(system_prompt, user_prompt)
            else:
                logger.warning(f"Unknown LLM provider '{self.provider}', falling back to local evaluation engine.")
                return None
        except Exception as exc:
            logger.error(f"External LLM call to '{self.provider}' failed: {exc}", exc_info=True)
            raise RuntimeError(f"LLM evaluation failed ({self.provider}): {str(exc)}") from exc

    def _call_openai_compatible(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call OpenAI chat completions API format."""
        base_url = self.api_base or "https://api.openai.com/v1"
        model_name = self.model or "gpt-4o-mini"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            raw_content = data["choices"][0]["message"]["content"]
            return self._clean_and_parse_json(raw_content)

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call Google Gemini REST API."""
        model_name = self.model or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"

        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0,
            },
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload, headers={"Content-Type": "application/json"})
            resp.raise_for_status()
            data = resp.json()
            raw_content = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._clean_and_parse_json(raw_content)

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call Anthropic Messages API."""
        model_name = self.model or "claude-3-5-haiku-20241022"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "system": system_prompt + "\nYou must reply strictly with a valid JSON object.",
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": 1024,
            "temperature": 0.0,
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            raw_content = data["content"][0]["text"]
            return self._clean_and_parse_json(raw_content)

    @staticmethod
    def _clean_and_parse_json(raw_text: str) -> Dict[str, Any]:
        """Extract and parse JSON object from LLM response text."""
        cleaned = raw_text.strip()
        # Remove markdown code fence if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned).strip()
        return json.loads(cleaned)


# Global singleton instance
llm_client = LLMClient()
