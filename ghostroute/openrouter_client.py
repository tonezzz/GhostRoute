from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

from .constants import OPENROUTER_CHAT_URL, OPENROUTER_MODELS_URL


@dataclass
class OpenRouterClient:
    api_key: str
    referer: str = "https://github.com/kittimasak/GhostRoute"
    title: str = "GhostRoute"
    timeout: int = 30
    max_retries: int = 3

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.referer,
            "X-Title": self.title,
        }

    def fetch_models(self) -> List[Dict[str, Any]]:
        """Fetch all models from OpenRouter API with simple retry/backoff."""
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = requests.get(
                    OPENROUTER_MODELS_URL,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [])
            except Exception as e:
                last_err = e
                # Exponential-ish backoff
                time.sleep(0.5 * (2**attempt))
        raise RuntimeError(f"Failed to fetch models: {last_err}")

    def health_check(self, model_id: str) -> Tuple[bool, Optional[str]]:
        """Minimal call to validate model availability.

        Returns (success, error_type).
        """
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5,
            "stream": False,
        }

        try:
            resp = requests.post(
                OPENROUTER_CHAT_URL,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return True, None
            if resp.status_code == 429:
                return False, "rate_limit"
            if resp.status_code == 503:
                return False, "unavailable"
            return False, f"error_{resp.status_code}"
        except requests.Timeout:
            return False, "timeout"
        except requests.RequestException:
            return False, "request_error"
