from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .constants import CACHE_DURATION_HOURS, DEFAULT_PATHS, FREE_ROUTER_ID
from .io_utils import read_json, atomic_write_json
from .openrouter_client import OpenRouterClient
from .ranking import is_free_model, rank_models


@dataclass
class ModelService:
    client: OpenRouterClient
    cache_file: Any = DEFAULT_PATHS.cache_file

    def _load_cache(self) -> Optional[List[Dict[str, Any]]]:
        cache = read_json(self.cache_file, default=None)
        if not cache:
            return None
        try:
            cached_at = datetime.fromisoformat(cache.get("cached_at", ""))
            if datetime.now() - cached_at < timedelta(hours=CACHE_DURATION_HOURS):
                return cache.get("models", [])
        except Exception:
            return None
        return None

    def _save_cache(self, models: List[Dict[str, Any]]) -> None:
        payload = {"cached_at": datetime.now().isoformat(), "models": models}
        atomic_write_json(self.cache_file, payload, indent=2)

    def get_ranked_free_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        if not force_refresh:
            cached = self._load_cache()
            if cached:
                return cached

        all_models = self.client.fetch_models()
        free_models = [m for m in all_models if is_free_model(m) or m.get("id") == FREE_ROUTER_ID]
        ranked = rank_models(free_models)
        self._save_cache(ranked)
        return ranked
