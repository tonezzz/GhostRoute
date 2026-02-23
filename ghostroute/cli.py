from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .auth import get_openrouter_api_key
from .constants import CACHE_DURATION_HOURS, DEFAULT_PATHS, FREE_ROUTER_ID
from .model_ids import format_for_openclaw
from .openclaw_config import OpenClawConfigManager
from .openrouter_client import OpenRouterClient
from .service import ModelService


def _require_api_key() -> str:
    api_key = get_openrouter_api_key(DEFAULT_PATHS.openclaw_config)
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        print("Set it via: export OPENROUTER_API_KEY='sk-or-...'")
        print("Or: openclaw config set env.OPENROUTER_API_KEY 'sk-or-...'\n")
        sys.exit(1)
    return api_key


def _model_service(force_title: str = "GhostRoute") -> ModelService:
    api_key = _require_api_key()
    client = OpenRouterClient(api_key=api_key, title=force_title)
    return ModelService(client=client)


def cmd_list(args) -> None:
    svc = _model_service()
    print("Fetching free models from OpenRouter...")
    models = svc.get_ranked_free_models(force_refresh=args.refresh)
    if not models:
        print("No free models available.")
        return

    mgr = OpenClawConfigManager(DEFAULT_PATHS.openclaw_config)
    cfg = mgr.load()
    current = mgr.get_primary(cfg)
    fallbacks = mgr.get_fallbacks(cfg)

    limit = args.limit
    print(f"\nTop {min(limit, len(models))} Free AI Models (ranked):\n")
    print(f"{'#':<3} {'Model ID':<55} {'Context':<12} {'Score':<7} {'Status'}")
    print("-" * 95)

    for i, m in enumerate(models[:limit], 1):
        mid = m.get("id", "unknown")
        context = int(m.get("context_length") or 0)
        score = float(m.get("_score") or 0.0)

        if context >= 1_000_000:
            context_str = f"{context // 1_000_000}M"
        elif context >= 1_000:
            context_str = f"{context // 1_000}K"
        else:
            context_str = str(context)

        formatted_primary = format_for_openclaw(mid, with_routing_prefix=True)
        formatted_fb = format_for_openclaw(mid, with_routing_prefix=False)
        status = ""
        if current and formatted_primary == current:
            status = "[PRIMARY]"
        elif formatted_fb in fallbacks or formatted_primary in fallbacks:
            status = "[FALLBACK]"

        print(f"{i:<3} {mid:<55} {context_str:<12} {score:.3f}  {status}")

    print(f"\nTotal free models available: {len(models)}")
    print("\nCommands:")
    print("  ghostroute switch <model>      Set as primary model")
    print("  ghostroute switch <model> -f   Add to fallbacks only")
    print("  ghostroute auto                Auto-select best model")


def _resolve_model(models: List[dict], query: str) -> Optional[str]:
    ids = [m.get("id", "") for m in models]
    if query in ids:
        return query
    q = query.lower()
    for mid in ids:
        if q in mid.lower():
            return mid
    return None


def _apply_config(
    model_id: str,
    as_primary: bool,
    fallback_count: int,
    setup_auth: bool,
    force_refresh_models: bool,
) -> None:
    mgr = OpenClawConfigManager(DEFAULT_PATHS.openclaw_config)
    cfg = mgr.ensure_structure(mgr.load())
    if setup_auth:
        cfg = mgr.setup_openrouter_auth_profile(cfg)

    formatted_primary = format_for_openclaw(model_id, with_routing_prefix=True)
    formatted_list = format_for_openclaw(model_id, with_routing_prefix=False)

    if as_primary:
        cfg["agents"]["defaults"]["model"]["primary"] = formatted_primary
        cfg["agents"]["defaults"]["models"].setdefault(formatted_list, {})

    # Build fallbacks
    svc = _model_service("GhostRoute Config")
    models = svc.get_ranked_free_models(force_refresh=force_refresh_models)

    fallbacks: List[str] = []
    if formatted_list != FREE_ROUTER_ID and formatted_primary != "openrouter/openrouter/free":
        fallbacks.append(FREE_ROUTER_ID)
        cfg["agents"]["defaults"]["models"].setdefault(FREE_ROUTER_ID, {})

    for m in models:
        mid = m.get("id", "")
        if not mid or FREE_ROUTER_ID in mid:
            continue

        fb = format_for_openclaw(mid, with_routing_prefix=False)
        fb_primary = format_for_openclaw(mid, with_routing_prefix=True)

        # skip primary
        if as_primary and (fb_primary == formatted_primary or fb == formatted_list):
            continue
        if len(fallbacks) >= fallback_count:
            break
        fallbacks.append(fb)
        cfg["agents"]["defaults"]["models"].setdefault(fb, {})

    # If configuring fallbacks-only, ensure chosen model is in the list (after router)
    if not as_primary:
        insert_pos = 1 if fallbacks and fallbacks[0] == FREE_ROUTER_ID else 0
        if formatted_list not in fallbacks:
            fallbacks.insert(insert_pos, formatted_list)
        cfg["agents"]["defaults"]["models"].setdefault(formatted_list, {})

    cfg["agents"]["defaults"]["model"]["fallbacks"] = fallbacks
    mgr.save(cfg)


def cmd_switch(args) -> None:
    svc = _model_service()
    models = svc.get_ranked_free_models(force_refresh=False)
    matched = _resolve_model(models, args.model)
    if not matched:
        print(f"Error: Model '{args.model}' not found in free models list.")
        print("Use 'ghostroute list' to see available models.")
        sys.exit(1)

    if args.fallback_only:
        print(f"Adding to fallbacks: {matched}")
    else:
        print(f"Setting as primary: {matched}")

    _apply_config(
        model_id=matched,
        as_primary=not args.fallback_only,
        fallback_count=args.fallback_count,
        setup_auth=args.setup_auth,
        force_refresh_models=False,
    )

    mgr = OpenClawConfigManager(DEFAULT_PATHS.openclaw_config)
    cfg = mgr.load()
    print("Success! OpenClaw config updated.")
    print(f"Primary model: {mgr.get_primary(cfg)}")
    fbs = mgr.get_fallbacks(cfg)
    if fbs:
        print(f"Fallback models ({len(fbs)}):")
        for fb in fbs[: min(10, len(fbs))]:
            print(f"  - {fb}")
        if len(fbs) > 10:
            print(f"  ... and {len(fbs) - 10} more")
    print("\nRestart OpenClaw for changes to take effect: openclaw gateway restart")


def cmd_auto(args) -> None:
    svc = _model_service()
    models = svc.get_ranked_free_models(force_refresh=True)
    if not models:
        print("Error: No free models available.")
        sys.exit(1)

    best = next((m for m in models if FREE_ROUTER_ID not in (m.get("id") or "")), models[0])
    model_id = best.get("id")
    if not model_id:
        print("Error: Could not determine best model.")
        sys.exit(1)

    if args.fallback_only:
        print("Keeping current primary, configuring fallbacks only.")
    else:
        print(f"Best free model: {model_id} (score {best.get('_score', 0):.3f})")

    _apply_config(
        model_id=model_id,
        as_primary=not args.fallback_only,
        fallback_count=args.fallback_count,
        setup_auth=args.setup_auth,
        force_refresh_models=True,
    )
    mgr = OpenClawConfigManager(DEFAULT_PATHS.openclaw_config)
    cfg = mgr.load()
    print("\nOpenClaw config updated!")
    print(f"Primary: {mgr.get_primary(cfg)}")
    print(f"Fallbacks ({len(mgr.get_fallbacks(cfg))}): {', '.join(mgr.get_fallbacks(cfg))}")
    print("\nRestart OpenClaw: openclaw gateway restart")


def cmd_status(_args) -> None:
    api_key = get_openrouter_api_key(DEFAULT_PATHS.openclaw_config)
    mgr = OpenClawConfigManager(DEFAULT_PATHS.openclaw_config)
    cfg = mgr.load()

    print("GhostRoute Status")
    print("=" * 50)
    if api_key:
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"OpenRouter API Key: {masked}")
    else:
        print("OpenRouter API Key: NOT SET")

    auth_profiles = cfg.get("auth", {}).get("profiles", {})
    print(f"OpenRouter Auth Profile: {'Configured' if 'openrouter:default' in auth_profiles else 'Not set'}")

    print(f"\nPrimary Model: {mgr.get_primary(cfg) or 'Not configured'}")
    fbs = mgr.get_fallbacks(cfg)
    if fbs:
        print(f"Fallback Models ({len(fbs)}):")
        for fb in fbs:
            print(f"  - {fb}")
    else:
        print("Fallback Models: None")

    print(f"\nOpenClaw Config: {DEFAULT_PATHS.openclaw_config} (exists: {DEFAULT_PATHS.openclaw_config.exists()})")


def cmd_refresh(_args) -> None:
    svc = _model_service()
    models = svc.get_ranked_free_models(force_refresh=True)
    print(f"Cached {len(models)} free models. Cache TTL: {CACHE_DURATION_HOURS}h")


def cmd_fallbacks(args) -> None:
    # Only rebuild fallbacks; keep primary
    mgr = OpenClawConfigManager(DEFAULT_PATHS.openclaw_config)
    cfg = mgr.ensure_structure(mgr.load())
    current = mgr.get_primary(cfg)
    print(f"Current primary: {current or 'None'}")
    print(f"Setting up {args.count} fallback models...")

    svc = _model_service()
    models = svc.get_ranked_free_models(force_refresh=False)
    fallbacks: List[str] = []

    # Always include openrouter/free first unless it's primary
    if current != "openrouter/openrouter/free":
        fallbacks.append(FREE_ROUTER_ID)
        cfg["agents"]["defaults"]["models"].setdefault(FREE_ROUTER_ID, {})

    for m in models:
        mid = m.get("id", "")
        if not mid or FREE_ROUTER_ID in mid:
            continue
        fb = format_for_openclaw(mid, with_routing_prefix=False)
        fb_primary = format_for_openclaw(mid, with_routing_prefix=True)
        if current and fb_primary == current:
            continue
        if len(fallbacks) >= args.count:
            break
        fallbacks.append(fb)
        cfg["agents"]["defaults"]["models"].setdefault(fb, {})

    cfg["agents"]["defaults"]["model"]["fallbacks"] = fallbacks
    mgr.save(cfg)
    print(f"\nConfigured {len(fallbacks)} fallback models:")
    for i, fb in enumerate(fallbacks, 1):
        print(f"  {i}. {fb}")
    print("\nRestart OpenClaw: openclaw gateway restart")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ghostroute",
        description="GhostRoute - Free AI for OpenClaw. Manage free models from OpenRouter.",
    )
    subs = parser.add_subparsers(dest="command")

    p_list = subs.add_parser("list", help="List available free models")
    p_list.add_argument("--limit", "-n", type=int, default=15)
    p_list.add_argument("--refresh", "-r", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_switch = subs.add_parser("switch", help="Switch to a specific model")
    p_switch.add_argument("model")
    p_switch.add_argument("--fallback-only", "-f", action="store_true")
    p_switch.add_argument("--setup-auth", action="store_true")
    p_switch.add_argument("--fallback-count", "-c", type=int, default=5)
    p_switch.set_defaults(func=cmd_switch)

    p_auto = subs.add_parser("auto", help="Auto-select best free model")
    p_auto.add_argument("--fallback-count", "-c", type=int, default=5)
    p_auto.add_argument("--fallback-only", "-f", action="store_true")
    p_auto.add_argument("--setup-auth", action="store_true")
    p_auto.set_defaults(func=cmd_auto)

    p_status = subs.add_parser("status", help="Show current configuration")
    p_status.set_defaults(func=cmd_status)

    p_refresh = subs.add_parser("refresh", help="Refresh model cache")
    p_refresh.set_defaults(func=cmd_refresh)

    p_fallbacks = subs.add_parser("fallbacks", help="Configure fallback models")
    p_fallbacks.add_argument("--count", "-c", type=int, default=5)
    p_fallbacks.set_defaults(func=cmd_fallbacks)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)
