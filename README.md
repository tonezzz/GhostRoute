# GhostRoute — Free AI Router for OpenClaw
### Zero-cost AI. Smart ranking. Multi-fallback failover. Optional auto-rotation.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![OpenClaw Compatible](https://img.shields.io/badge/OpenClaw-Compatible-blue.svg)](https://github.com/openclaw/openclaw)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Free%20Models-orange.svg)](https://openrouter.ai)

---

GhostRoute keeps **OpenClaw** running on **OpenRouter’s free models** by automatically:

- picking the **best free primary** (ranked)
- building a **fallback chain** that survives 429/503
- *(optional)* rotating your primary over time with a watcher daemon
- updating `~/.openclaw/openclaw.json` safely while preserving your setup

> Think of it as “**$0 AI** with **paid-tier smoothness**.”

---

## ⚡ TL;DR (60 seconds)

```bash
npx clawhub@latest install ghostroute
cd ~/.openclaw/workspace/skills/ghost-route
pip install -e .

export OPENROUTER_API_KEY="sk-or-v1-..."
ghostroute auto
openclaw gateway restart
````

Want maximum uptime?

```bash
ghostroute-watcher --daemon
```

---

## Why GhostRoute exists

OpenClaw is awesome — until reality hits:

* 💸 Token bills grow faster than you think (especially with long contexts)
* 🚦 Free tiers throttle hard (429s), providers get busy (503), latency spikes
* 🔁 Manually hopping between models breaks flow and wastes time
* 🎲 The “best free model” changes constantly as availability and limits shift

GhostRoute makes free models *usable* for real work by automating the boring parts.

---

## What you get

After `ghostroute auto`, your OpenClaw config will look like:

```text
Primary Model: openrouter/<provider>/<model>:free

Fallbacks:
  1. openrouter/free          ← Smart router (capability-aware)
  2. <provider>/<model>:free  ← Ranked fallback #1
  3. <provider>/<model>:free  ← Ranked fallback #2
  ...
```

When a model rate-limits or becomes unavailable, OpenClaw tries the next fallback automatically — you keep working.

---

## Installation

```bash
npx clawhub@latest install ghostroute
cd ~/.openclaw/workspace/skills/ghost-route
pip install -e .
```

This installs two commands:

* `ghostroute` (CLI)
* `ghostroute-watcher` (optional daemon)

---

## Prerequisites

### 1) Create a free OpenRouter key

Go to: [https://openrouter.ai/keys](https://openrouter.ai/keys)
Create account → Generate key (no credit card required)

### 2) Set your key

Recommended (env var):

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

Or store in OpenClaw config:

```bash
openclaw config set env.OPENROUTER_API_KEY "sk-or-v1-..."
```

---

## Quick Start

### 1) Auto-configure the best free model + fallbacks

```bash
ghostroute auto
```

### 2) Restart OpenClaw to apply changes

```bash
openclaw gateway restart
```

### 3) Verify (in your agent chat)

Send:

* `/status` → shows active model + tokens
* `/model` → shows available models
* `/new` → start a clean session

---

## Best Presets (copy/paste)

### Balanced (recommended for most users)

```bash
ghostroute auto
openclaw gateway restart
```

### Max uptime (heavy usage / long sessions)

```bash
ghostroute auto -c 10
openclaw gateway restart
ghostroute-watcher --daemon
```

### Keep current primary, add strong protection

```bash
ghostroute auto -f -c 10
openclaw gateway restart
```

---

## Commands

| Command                        | What it does                                 |
| ------------------------------ | -------------------------------------------- |
| `ghostroute auto`              | Auto-configure best free primary + fallbacks |
| `ghostroute auto -f`           | Keep current primary, update fallbacks only  |
| `ghostroute auto -c 10`        | Increase fallback count (default is 5)       |
| `ghostroute list`              | Show ranked free models                      |
| `ghostroute list -n 30`        | Show more results                            |
| `ghostroute switch <model>`    | Set a specific model as primary              |
| `ghostroute switch <model> -f` | Add a specific model as fallback only        |
| `ghostroute status`            | Show key status + config + cache             |
| `ghostroute fallbacks`         | Update only the fallback list                |
| `ghostroute refresh`           | Force refresh cached model catalog           |

After any command that changes config:

```bash
openclaw gateway restart
```

---

## How ranking works (simple + practical)

GhostRoute scores each free model (0–1) using:

| Factor         | Weight | Why it matters                           |
| -------------- | -----: | ---------------------------------------- |
| Context Length |    40% | Larger context = bigger codebases & docs |
| Capabilities   |    30% | Tools, structured output, vision support |
| Recency        |    20% | Newer models tend to perform better      |
| Provider Trust |    10% | Reliability across major providers       |

The first fallback is always:

* `openrouter/free` — a smart router that picks a compatible free model based on request needs.

---

## What GhostRoute writes (and what it never touches)

GhostRoute updates only these keys in `~/.openclaw/openclaw.json`:

* `agents.defaults.model.primary`
* `agents.defaults.model.fallbacks`
* `agents.defaults.models` (allowlist so `/model` shows them)

Everything else is preserved:

* gateway, channels, plugins, workspace, env, custom instructions, named agents

---

## Watcher (Auto-Rotation) — Optional but powerful

Watcher is “uptime mode” for free models.

```bash
ghostroute-watcher                 # run once (check + rotate if needed)
ghostroute-watcher --daemon        # continuous monitoring
ghostroute-watcher --rotate        # force rotate now
ghostroute-watcher --status        # view cooldowns / rotation history
ghostroute-watcher --clear-cooldowns
```

When it detects repeated throttling:

* it cools down rate-limited models
* rotates primary to the next best available free model
* keeps `openrouter/free` at the top of fallbacks

---

## Testing with OpenClaw

```bash
openclaw models list
openclaw doctor --fix
openclaw dashboard
```

Agent commands:

* `/status` current model + tokens
* `/model` available models
* `/new` fresh session

---

## Troubleshooting (fast fixes)

| Problem                           | Fix                                                                                            |
| --------------------------------- | ---------------------------------------------------------------------------------------------- |
| `ghostroute: command not found`   | `cd ~/.openclaw/workspace/skills/ghost-route && pip install -e .`                              |
| `OPENROUTER_API_KEY not set`      | Create at [https://openrouter.ai/keys](https://openrouter.ai/keys) then export/set in OpenClaw |
| Changes not taking effect         | `openclaw gateway restart` then send `/new`                                                    |
| Too many 429s                     | `ghostroute auto -c 10` + `ghostroute-watcher --daemon`                                        |
| `/model` doesn’t show free models | run `ghostroute auto` again + restart gateway                                                  |

---

## Security / Privacy note (free endpoints)

Free endpoints/providers may have different logging policies.
Avoid sending secrets, credentials, or sensitive personal data unless you’re confident in the provider policy.

---

## Architecture (Single Diagram)

```text
┌───────────────────────────────────────────────────────────────────┐
│ YOU (commands)                                                     │
│  • ghostroute auto / switch                                        │
│  • ghostroute-watcher --daemon                                     │
└───────────────────────────────┬───────────────────────────────────┘
                                │ (1) Setup / Update config
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ GHOSTROUTE (CLI)                                                   │
│  • Load OPENROUTER_API_KEY                                         │
│  • Fetch /api/v1/models                                            │
│  • Filter free models (:free / prompt=0)                           │
│  • Rank + select primary                                           │
│  • Build fallbacks (always includes: openrouter/free)              │
└───────────────────────────────┬───────────────────────────────────┘
                                │ HTTPS
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ OPENROUTER API                                                     │
│  • GET  /api/v1/models        (metadata / pricing / context)       │
│  • POST /chat/completions     (runtime inference)                  │
└───────────────────────────────┬───────────────────────────────────┘
                                │ (2) Write OpenClaw config (atomic)
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ LOCAL MACHINE                                                      │
│  ~/.openclaw/openclaw.json                                         │
│   • agents.defaults.model.primary                                  │
│   • agents.defaults.model.fallbacks                                │
│   • agents.defaults.models (allowlist)                             │
│  + cache/state (ghostroute cache + watcher state)                  │
└───────────────────────────────┬───────────────────────────────────┘
                                │ (3) Apply config
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ OPENCLAW GATEWAY                                                   │
│  • openclaw gateway restart                                        │
└───────────────────────────────┬───────────────────────────────────┘
                                │ (4) Runtime requests + failover
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ OPENCLAW (Agents / Channels)                                       │
│  Primary ──► OpenRouter POST /chat/completions                     │
│     ├─ 200 OK  ──► respond to user                                 │
│     └─ 429/503 ─► Fallback Engine ─► try next fallback(s)          │
│                  (openrouter/free is usually first)                │
└───────────────────────────────┬───────────────────────────────────┘
                                │ (optional) Long-run uptime mode
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ GHOSTROUTE WATCHER (optional daemon)                               │
│  • Health-check current primary                                    │
│  • Cooldown models that rate-limit (429)                           │
│  • Rotate primary → next best available free model                 │
│  • Rewrite fallbacks (keep openrouter/free at top)                 │
│  • then: openclaw gateway restart (to apply new primary)           │
└───────────────────────────────────────────────────────────────────┘
```

---

## Requirements

* OpenClaw installed (Node ≥22)
* Python 3.8+
* Free OpenRouter account ([https://openrouter.ai/keys](https://openrouter.ai/keys))

---

## Contributing

PRs welcome.

```bash
cd ~/.openclaw/workspace/skills/ghost-route
ghostroute list
ghostroute status
ghostroute auto --help
```

---

## License

MIT — do whatever you want.

<p align="center">
  <a href="https://github.com/kittimasak/GhostRoute">⭐ Star on GitHub</a>
  ·
  <a href="https://openrouter.ai/keys">🔑 Get OpenRouter Key</a>
  ·
  <a href="https://github.com/openclaw/openclaw">🦞 Install OpenClaw</a>
</p>
```
# GhostRoute
