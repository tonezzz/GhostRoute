from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    openclaw_config: Path
    cache_file: Path
    watcher_state_file: Path


DEFAULT_PATHS = Paths(
    openclaw_config=Path.home() / ".openclaw" / "openclaw.json",
    cache_file=Path.home() / ".openclaw" / ".ghostroute-cache.json",
    watcher_state_file=Path.home() / ".openclaw" / ".ghostroute-watcher-state.json",
)


OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


# Cache duration
CACHE_DURATION_HOURS = 6


# Ranking weights (higher is better)
RANKING_WEIGHTS = {
    "context_length": 0.40,
    "capabilities": 0.30,
    "recency": 0.20,
    "provider_trust": 0.10,
}


TRUSTED_PROVIDERS = [
    "google",
    "openai",
    "anthropic",
    "meta-llama",
    "mistralai",
    "deepseek",
    "nvidia",
    "qwen",
    "microsoft",
    "allenai",
    "arcee-ai",
]


# Watcher defaults
RATE_LIMIT_COOLDOWN_MINUTES = 30
CHECK_INTERVAL_SECONDS = 60


# OpenRouter router for free models
FREE_ROUTER_ID = "openrouter/free"
