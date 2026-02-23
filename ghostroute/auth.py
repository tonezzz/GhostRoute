from __future__ import annotations

import os
from typing import Optional

from .openclaw_config import OpenClawConfigManager


def get_openrouter_api_key(config_path=None) -> Optional[str]:
    """Get OpenRouter API key from env or OpenClaw config."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        return api_key

    mgr = OpenClawConfigManager(path=config_path) if config_path else OpenClawConfigManager()
    cfg = mgr.load()
    return cfg.get("env", {}).get("OPENROUTER_API_KEY")
