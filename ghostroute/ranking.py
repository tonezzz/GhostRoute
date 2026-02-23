from __future__ import annotations

import math
import time
from typing import Any, Dict, List

from .constants import RANKING_WEIGHTS, TRUSTED_PROVIDERS


def is_free_model(model: Dict[str, Any]) -> bool:
    """Best-effort check for free-tier models.

    OpenRouter model payloads usually contain a `pricing` object.
    We consider a model free if prompt cost is 0 OR the model id contains `:free`.
    """
    model_id = str(model.get("id", ""))
    pricing = model.get("pricing", {}) or {}
    prompt_cost = pricing.get("prompt")
    if ":free" in model_id:
        return True
    if prompt_cost is None:
        return False
    try:
        return float(prompt_cost) == 0.0
    except (ValueError, TypeError):
        return False


def _score_context_length(context_length: int) -> float:
    """Log-scale context score (more stable than linear).

    - 4K  ~ 0.25
    - 32K ~ 0.45
    - 128K~ 0.60
    - 1M  ~ 1.00
    """
    if not context_length:
        return 0.0
    # Map to 0..1 using log10, clamp at 1M
    clamped = max(1, min(int(context_length), 1_000_000))
    return min(math.log10(clamped) / math.log10(1_000_000), 1.0)


def _score_capabilities(model: Dict[str, Any]) -> float:
    caps = model.get("supported_parameters") or []
    # Normalize against 12 to avoid early saturation
    return min(len(caps) / 12.0, 1.0)


def _score_recency(created_epoch: int) -> float:
    if not created_epoch:
        return 0.0
    days_old = (time.time() - float(created_epoch)) / 86400.0
    # Half-life style: 0.5 at 180 days, ~0.25 at 360 days
    return max(0.0, 2 ** (-days_old / 180.0))


def _score_provider_trust(model_id: str) -> float:
    provider = model_id.split("/")[0] if "/" in model_id else ""
    if provider not in TRUSTED_PROVIDERS:
        return 0.0
    # Higher for earlier providers
    idx = TRUSTED_PROVIDERS.index(provider)
    return 1.0 - (idx / max(1, len(TRUSTED_PROVIDERS) - 1))


def calculate_model_score(model: Dict[str, Any]) -> float:
    model_id = str(model.get("id", ""))
    context_length = int(model.get("context_length") or 0)
    created = int(model.get("created") or 0)

    score = 0.0
    score += _score_context_length(context_length) * RANKING_WEIGHTS["context_length"]
    score += _score_capabilities(model) * RANKING_WEIGHTS["capabilities"]
    score += _score_recency(created) * RANKING_WEIGHTS["recency"]
    score += _score_provider_trust(model_id) * RANKING_WEIGHTS["provider_trust"]
    return float(score)


def rank_models(models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scored = [{**m, "_score": calculate_model_score(m)} for m in models]
    scored.sort(key=lambda x: x.get("_score", 0.0), reverse=True)
    return scored
