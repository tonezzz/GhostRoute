from __future__ import annotations

from .constants import FREE_ROUTER_ID


def format_for_openclaw(model_id: str, with_routing_prefix: bool) -> str:
    """Format a model id for OpenClaw config.

    OpenClaw commonly uses:
    - primary:   openrouter/<provider>/<model>:free
    - fallbacks: <provider>/<model>:free (and openrouter/free router id)

    Special case: OpenRouter's router id itself is "openrouter/free".
    When used as OpenClaw primary, it must be "openrouter/openrouter/free".
    """
    if model_id in (FREE_ROUTER_ID, f"{FREE_ROUTER_ID}:free"):
        return "openrouter/openrouter/free" if with_routing_prefix else FREE_ROUTER_ID

    base = model_id
    if base.startswith("openrouter/"):
        base = base[len("openrouter/"):]

    if ":free" not in base:
        base = f"{base}:free"

    return f"openrouter/{base}" if with_routing_prefix else base
