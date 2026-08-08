# Thief Agent

This repository contains the **Thief** peer for the distributed
Cops-and-Robbers game. The Police peer lives in the separate
[`Moaawiyah/police-agent`](https://github.com/Moaawiyah/police-agent) repository.
Each side runs as an independent process, hosts its own
[FastMCP](https://github.com/jlowin/fastmcp) server, and acts as an MCP client
toward the other.

There is no central game server or referee. Both peers derive the same outcome
from the shared rules and verify each other's moves cryptographically.

## Repository boundary

Role-specific files belong to this repository:

- `config/thief/game.toml.example` — Thief network, strategy, and local settings;
- `src/thief_agent/__init__.py` — identifies this package as the Thief peer;
- `src/thief_agent/strategy/` — Thief belief and move policy;
- `src/thief_agent/peer/` — handshake, runtime, and turn orchestration.

The deterministic game vocabulary and rules remain shared so this peer stays
wire-compatible with the Police repository:

- `config/thief/game.json` — this repository's copy of the agreed game rules;
- `src/thief_agent/constants.py`;
- `src/thief_agent/domain/`;
- corresponding shared tests.

When shared rules change, apply the same change to the Police repository and
run both repositories' test suites.

## Status

The Thief runtime, reference-compatible protocol, handshake, commit-reveal
audit, configuration loader, FastMCP transport, full pheromone mechanics,
Bayesian belief fusion, public SDK, series aggregation, reporting, and GUI are
implemented. Role alternation remains owned by the separate Police peer.
See [`PLAN.md`](docs/PLAN.md) for the build order and [`TODO.md`](docs/TODO.md) for the
current step.

## Layout

```
src/thief_agent/
  domain/   shared game rules, board, movement, and scoring
  infra/    Thief-side FastMCP server/client, email, and LLM provider
  peer/     Thief orchestration, handshake, and turn handling
  sdk/      lazy public composition root for callers and front ends
  gui/      live/replay Tk heatmap and immutable view rendering
  shared/   shared config loading and rate limiting
config/
  thief/    Thief's private config + its copy of the shared game.json
tests/      shared domain tests and Thief-specific tests
```

## Running

```
uv sync
cp config/thief/game.toml.example config/thief/game.toml
uv run thief-agent play --config-dir config/thief
uv run thief-agent gui --config-dir config/thief
uv run thief-agent replay result.json --config-dir config/thief
# mailbox-only mode (debugging/interop tools)
uv run thief-agent server --port 8802
uv run pytest
uv run ruff check .
```

The example private config selects local Ollama (`qwen3:4b`) for dialogue. If
Ollama is unavailable, the Thief automatically sends a bounded template hint;
movement and legality never depend on the model.
