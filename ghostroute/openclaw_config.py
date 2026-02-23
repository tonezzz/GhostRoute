from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .constants import DEFAULT_PATHS
from .io_utils import read_json, atomic_write_json


@dataclass
class OpenClawConfigManager:
    path: Path = DEFAULT_PATHS.openclaw_config

    def load(self) -> Dict[str, Any]:
        return read_json(self.path, default={})

    def save(self, config: Dict[str, Any]) -> None:
        atomic_write_json(self.path, config, indent=2)

    @staticmethod
    def ensure_structure(config: Dict[str, Any]) -> Dict[str, Any]:
        config.setdefault("agents", {})
        config["agents"].setdefault("defaults", {})
        config["agents"]["defaults"].setdefault("model", {})
        config["agents"]["defaults"].setdefault("models", {})
        return config

    @staticmethod
    def get_primary(config: Dict[str, Any]) -> Optional[str]:
        return config.get("agents", {}).get("defaults", {}).get("model", {}).get("primary")

    @staticmethod
    def get_fallbacks(config: Dict[str, Any]) -> List[str]:
        return config.get("agents", {}).get("defaults", {}).get("model", {}).get("fallbacks", [])

    @staticmethod
    def setup_openrouter_auth_profile(config: Dict[str, Any]) -> Dict[str, Any]:
        config.setdefault("auth", {})
        config["auth"].setdefault("profiles", {})
        config["auth"]["profiles"].setdefault(
            "openrouter:default",
            {"provider": "openrouter", "mode": "api_key"},
        )
        return config
