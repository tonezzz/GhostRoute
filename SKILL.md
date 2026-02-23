---
name: ghostroute
author: Dr.Kittimasak Naijit
description: "Keeps OpenClaw running on OpenRouter free models with smart ranking, multi-level fallbacks, and optional auto-rotation. Automatically updates ~/.openclaw/openclaw.json (atomic writes) so you get $0 AI without workflow interruptions. Use when users mention OpenRouter free models, rate limits (429), model switching, or reducing AI costs."
---

# GhostRoute — Free AI for OpenClaw (Ranked + Fallbacks + Auto-Rotation)

GhostRoute is an OpenClaw skill that turns OpenRouter’s **free models** into a reliable, always-on setup.

It does three things extremely well:

1) **Chooses the best free model** available (as your Primary)  
2) **Builds a strong fallback chain** so 429/503 doesn’t stop you  
3) *(Optional)* runs a **Watcher** to auto-rotate your Primary over time

> Result: **$0/month AI**, but with a workflow that feels “paid-tier smooth”.

---

## What This Skill Does (in plain English)

When you run:

```bash
ghostroute auto
````

GhostRoute will:

* Fetch the current model catalog from OpenRouter
* Detect which models are **free** (e.g., `:free` / free prompt pricing)
* Rank free models by usefulness (context, capability, recency, provider trust)
* Write your OpenClaw config so:

  * **Primary** = best ranked free model
  * **Fallbacks** = `openrouter/free` + next best free models
  * **Allowlist models** so `/model` displays them

Then you apply it with:

```bash
openclaw gateway restart
```

Your OpenClaw agent continues working even when one provider throttles you.

---

## Mental Model: 2 Layers of Protection

### Layer A — OpenClaw Fallback Engine (instant safety)

During runtime, OpenClaw automatically tries the next fallback when the primary hits:

* **429** (rate limit / throttle)
* **503** (provider busy / unavailable)

This means: **no interruptions mid-session**.

### Layer B — GhostRoute Watcher (long-run uptime mode)

Watcher is optional, but powerful when you run long sessions.

It continuously:

* health-checks the current primary
* cools down models that rate-limit
* rotates primary to a better available free model

---

## Implementation Notes (v1.1+)

GhostRoute ships as a small Python package (`ghostroute/`) so the CLI and watcher stay consistent:

* **Single source of truth** for ranking + OpenRouter calls + config writing
* **Atomic config writes** to reduce risk of `openclaw.json` corruption
* **Consistent headers / retry behavior** across CLI and watcher

The classic entrypoints remain for compatibility:

* `main.py` → `ghostroute`
* `watcher.py` → `ghostroute-watcher`

---

## Prerequisites (must have)

### 1) OpenRouter API Key

Check:

```bash
echo $OPENROUTER_API_KEY
```

If empty, generate a key at:

* [https://openrouter.ai/keys](https://openrouter.ai/keys)  

Set it (recommended):

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

Or persist via OpenClaw:

```bash
openclaw config set env.OPENROUTER_API_KEY "sk-or-v1-..."
```

### 2) GhostRoute installed

Check:

```bash
which ghostroute
```

If not found:

```bash
cd ~/.openclaw/workspace/skills/ghost-route
pip install -e .
```

---

## Primary Workflow (recommended)

> Use this when the user wants “free AI setup” with minimal steps.

```bash
# 1) Configure best free model + fallbacks
ghostroute auto

# 2) Apply changes
openclaw gateway restart
```

Verification (in the agent):

* send `/status` to see active model name + token counter  

---

## Commands Reference (when to use what)

| Command                        | Use when…                                     | Example                            |
| ------------------------------ | --------------------------------------------- | ---------------------------------- |
| `ghostroute auto`              | Most common: user wants free AI configured    | `ghostroute auto`                  |
| `ghostroute auto -f`           | Keep existing primary, only rebuild fallbacks | `ghostroute auto -f`               |
| `ghostroute auto -c 10`        | Need more fallbacks for uptime                | `ghostroute auto -c 10`            |
| `ghostroute list`              | User wants to see ranked free models          | `ghostroute list`                  |
| `ghostroute list -n 30`        | Show more results                             | `ghostroute list -n 30`            |
| `ghostroute switch <model>`    | User wants a specific free model              | `ghostroute switch qwen3-coder`    |
| `ghostroute switch <model> -f` | Add model as fallback only                    | `ghostroute switch qwen3-coder -f` |
| `ghostroute status`            | Debug configuration + cache                   | `ghostroute status`                |
| `ghostroute fallbacks`         | Rebuild only fallback list                    | `ghostroute fallbacks -c 8`        |
| `ghostroute refresh`           | Force refresh cached model catalog            | `ghostroute refresh`               |

✅ **After any command that changes config, always run:**

```bash
openclaw gateway restart
```

---

## What It Writes to OpenClaw Config (exact keys)

GhostRoute updates only these keys in:

`~/.openclaw/openclaw.json`

* `agents.defaults.model.primary`
  Example: `openrouter/qwen/qwen3-coder:free`

* `agents.defaults.model.fallbacks`
  Example: `["openrouter/free", "nvidia/nemotron-3-nano-30b-a3b:free", ...]`

* `agents.defaults.models`
  Allowlist so `/model` shows these free models  

Everything else is preserved:

* gateway, channels, plugins, env, customInstructions, named agents, workspace settings  

### Why is `openrouter/free` the first fallback?

Because it’s OpenRouter’s “smart router” that auto-picks the best available free model based on your request (capability-aware fallback).

---

## Watcher (Optional — recommended for long sessions)

Use watcher when:

* you frequently hit 429
* you want “hands-free uptime”
* you run OpenClaw for hours/days

```bash
ghostroute-watcher --daemon     # continuous monitoring
ghostroute-watcher --rotate     # force rotate now
ghostroute-watcher --status     # view rotation history/cooldowns
ghostroute-watcher --clear-cooldowns
```

> Tip: watcher keeps models in a cooldown window after 429 to avoid retry loops.

---

## Troubleshooting (fast fixes)

| Symptom                           | Likely Cause          | Fix                                                                               |
| --------------------------------- | --------------------- | --------------------------------------------------------------------------------- |
| `ghostroute: command not found`   | Not installed / PATH  | `cd ~/.openclaw/workspace/skills/ghost-route && pip install -e .`                 |
| `OPENROUTER_API_KEY not set`      | missing key           | create at [https://openrouter.ai/keys](https://openrouter.ai/keys) and export it  |
| Changes not taking effect         | gateway not restarted | `openclaw gateway restart` then send `/new`                                       |
| Too many 429s                     | too few fallbacks     | `ghostroute auto -c 10` + `ghostroute-watcher --daemon`                           |
| `/model` doesn’t show free models | allowlist not applied | run `ghostroute auto`, restart gateway                                            |

---

## Best Practices (recommended defaults)

### Most users (balanced)

```bash
ghostroute auto
openclaw gateway restart
```

### Max uptime (heavy usage)

```bash
ghostroute auto -c 10
openclaw gateway restart
ghostroute-watcher --daemon
```

### Keep your favorite primary, but protect with fallbacks

```bash
ghostroute auto -f -c 10
openclaw gateway restart
```

---

## Safety Note (free endpoints)

Some free endpoints/providers may log prompts/outputs.
Avoid sending secrets, credentials, or sensitive personal data unless you are sure about the provider policy.

---
