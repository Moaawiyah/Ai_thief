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
- `src/police_thief/__init__.py` — identifies this package as the Thief peer;
- future Thief strategy, orchestration, and runtime modules.

The deterministic game vocabulary and rules remain shared so this peer stays
wire-compatible with the Police repository:

- `config/thief/game.json` — this repository's copy of the agreed game rules;
- `src/police_thief/constants.py`;
- `src/police_thief/domain/`;
- corresponding shared tests.

When shared rules change, apply the same change to the Police repository and
run both repositories' test suites.

## Status

Project setup and deterministic domain rules are implemented. Thief networking,
strategy, and reporting are not implemented yet. See [`PLAN.md`](PLAN.md) for
the build order and [`TODO.md`](TODO.md) for the current step.

## Layout

```
src/police_thief/
  domain/   shared game rules, board, movement, and scoring
  infra/    Thief-side FastMCP server/client, email, and LLM provider
  peer/     Thief orchestration, handshake, and turn handling
  shared/   shared config loading and rate limiting
config/
  thief/    Thief's private config + its copy of the shared game.json
tests/      shared domain tests and Thief-specific tests
```

## Running

```
uv sync
uv run thief-agent
uv run pytest
uv run ruff check .
```
