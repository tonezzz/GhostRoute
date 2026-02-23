from __future__ import annotations

import argparse
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

from .auth import get_openrouter_api_key
from .constants import (
    CHECK_INTERVAL_SECONDS,
    DEFAULT_PATHS,
    FREE_ROUTER_ID,
    RATE_LIMIT_COOLDOWN_MINUTES,
)
from .model_ids import format_for_openclaw
from .openclaw_config import OpenClawConfigManager
from .openrouter_client import OpenRouterClient
from .service import ModelService
from .io_utils import read_json, atomic_write_json


def load_state() -> Dict:
    return read_json(
        DEFAULT_PATHS.watcher_state_file,
        default={"rate_limited_models": {}, "rotation_count": 0},
    )


def save_state(state: Dict) -> None:
    atomic_write_json(DEFAULT_PATHS.watcher_state_file, state, indent=2)


def is_in_cooldown(state: Dict, model_id: str) -> bool:
    limited_at_str = (state.get("rate_limited_models") or {}).get(model_id)
    if not limited_at_str:
        return False
    try:
        limited_at = datetime.fromisoformat(limited_at_str)
    except Exception:
        return False
    return datetime.now() < (limited_at + timedelta(minutes=RATE_LIMIT_COOLDOWN_MINUTES))


def mark_cooldown(state: Dict, model_id: str) -> None:
    state.setdefault("rate_limited_models", {})
    state["rate_limited_models"][model_id] = datetime.now().isoformat()
    save_state(state)


def cleanup_cooldowns(state: Dict) -> None:
    rl = state.get("rate_limited_models") or {}
    now = datetime.now()
    expired = []
    for mid, ts in rl.items():
        try:
            t = datetime.fromisoformat(ts)
            if now - t > timedelta(minutes=RATE_LIMIT_COOLDOWN_MINUTES):
                expired.append(mid)
        except Exception:
            expired.append(mid)
    for mid in expired:
        rl.pop(mid, None)
    if expired:
        save_state(state)


def pick_next_model(svc: ModelService, client: OpenRouterClient, state: Dict, exclude: Optional[str]) -> Optional[str]:
    models = svc.get_ranked_free_models(force_refresh=False)
    for m in models:
        mid = m.get("id")
        if not mid or FREE_ROUTER_ID in mid:
            continue
        if exclude and mid == exclude:
            continue
        if is_in_cooldown(state, mid):
            continue
        ok, err = client.health_check(mid)
        if ok:
            return mid
        if err == "rate_limit":
            mark_cooldown(state, mid)
    return None


def rotate(reason: str) -> bool:
    api_key = get_openrouter_api_key(DEFAULT_PATHS.openclaw_config)
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        return False

    client = OpenRouterClient(api_key=api_key, title="GhostRoute Watcher")
    svc = ModelService(client=client)
    state = load_state()
    cleanup_cooldowns(state)

    mgr = OpenClawConfigManager(DEFAULT_PATHS.openclaw_config)
    cfg = mgr.ensure_structure(mgr.load())
    current = mgr.get_primary(cfg)

    current_base = None
    if current:
        current_base = current[len("openrouter/"):] if current.startswith("openrouter/") else current

    print(f"[{datetime.now().isoformat()}] Rotating from: {current_base or 'none'}")
    print(f"  Reason: {reason}")

    next_mid = pick_next_model(svc, client, state, exclude=current_base)
    if not next_mid:
        print("  Error: No available models found")
        return False

    formatted_primary = format_for_openclaw(next_mid, with_routing_prefix=True)
    cfg["agents"]["defaults"]["model"]["primary"] = formatted_primary

    # allowlist
    cfg["agents"]["defaults"]["models"].setdefault(
        format_for_openclaw(next_mid, with_routing_prefix=False),
        {},
    )

    # rebuild fallbacks
    fallbacks = [FREE_ROUTER_ID]
    cfg["agents"]["defaults"]["models"].setdefault(FREE_ROUTER_ID, {})
    models = svc.get_ranked_free_models(force_refresh=False)
    for m in models:
        mid = m.get("id")
        if not mid or mid == next_mid or FREE_ROUTER_ID in mid:
            continue
        if is_in_cooldown(state, mid):
            continue
        fb = format_for_openclaw(mid, with_routing_prefix=False)
        fallbacks.append(fb)
        cfg["agents"]["defaults"]["models"].setdefault(fb, {})
        if len(fallbacks) >= 5:
            break
    cfg["agents"]["defaults"]["model"]["fallbacks"] = fallbacks

    mgr.save(cfg)

    state["rotation_count"] = int(state.get("rotation_count") or 0) + 1
    state["last_rotation"] = datetime.now().isoformat()
    state["last_rotation_reason"] = reason
    save_state(state)

    print(f"  Success! Rotated to {next_mid}")
    print("  Note: restart OpenClaw gateway for changes to take effect")
    return True


def check_once() -> None:
    api_key = get_openrouter_api_key(DEFAULT_PATHS.openclaw_config)
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        sys.exit(1)

    client = OpenRouterClient(api_key=api_key, title="GhostRoute Watcher")
    svc = ModelService(client=client)
    state = load_state()
    cleanup_cooldowns(state)

    mgr = OpenClawConfigManager(DEFAULT_PATHS.openclaw_config)
    cfg = mgr.load()
    current = mgr.get_primary(cfg)
    if not current:
        rotate("initial_setup")
        return

    current_base = current[len("openrouter/"):] if current.startswith("openrouter/") else current
    if is_in_cooldown(state, current_base):
        rotate("cooldown_active")
        return

    print(f"[{datetime.now().isoformat()}] Testing: {current_base}")
    ok, err = client.health_check(current_base)
    if ok:
        print("  Status: OK")
        return
    print(f"  Status: {err}")
    if err == "rate_limit":
        mark_cooldown(state, current_base)
    rotate(err or "unknown_error")


def run_daemon() -> None:
    running = True

    def _sig(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)

    print("GhostRoute Watcher started")
    print(f"Check interval: {CHECK_INTERVAL_SECONDS}s")
    print(f"Rate limit cooldown: {RATE_LIMIT_COOLDOWN_MINUTES}m")
    print("-" * 50)

    while running:
        try:
            check_once()
        except Exception as e:
            print(f"Error during check: {e}")
        for _ in range(CHECK_INTERVAL_SECONDS):
            if not running:
                break
            time.sleep(1)
    print("Watcher stopped")


def main() -> None:
    p = argparse.ArgumentParser(
        prog="ghostroute-watcher",
        description="GhostRoute Watcher - Monitor and auto-rotate free AI models",
    )
    p.add_argument("--daemon", "-d", action="store_true")
    p.add_argument("--rotate", "-r", action="store_true")
    p.add_argument("--status", "-s", action="store_true")
    p.add_argument("--clear-cooldowns", action="store_true")

    args = p.parse_args()
    state = load_state()

    if args.status:
        print("GhostRoute Watcher Status")
        print("=" * 40)
        print(f"Total rotations: {state.get('rotation_count', 0)}")
        print(f"Last rotation: {state.get('last_rotation', 'Never')}")
        print(f"Last reason: {state.get('last_rotation_reason', 'N/A')}")
        print("\nModels in cooldown:")
        rl = state.get("rate_limited_models") or {}
        if not rl:
            print("  None")
        else:
            for mid, ts in rl.items():
                print(f"  - {mid} (since {ts})")
        return

    if args.clear_cooldowns:
        state["rate_limited_models"] = {}
        save_state(state)
        print("Cleared all rate limit cooldowns")
        return

    if args.rotate:
        rotate("manual_rotation")
        return

    if args.daemon:
        run_daemon()
        return

    check_once()
