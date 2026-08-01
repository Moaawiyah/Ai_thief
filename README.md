# Police-Thief P2P

Distributed Cops-and-Robbers game over a peer-to-peer network. Two independent
agents — **Police** and **Thief** — run as separate processes, each hosting
its own [FastMCP](https://github.com/jlowin/fastmcp) server and acting as an
MCP client toward the other. There is no central game server and no central
referee: both sides derive the same outcome from a signed, shared rules file
(`config/*/game.json`) and verify each other's moves cryptographically.

Full specification: [`police_thief_p2p.pdf`](police_thief_p2p.pdf). Project
conventions and the incremental build order live in [`CLAUDE.md`](CLAUDE.md).

## Status

Project setup only — game rules, networking, strategy, and reporting are not
implemented yet. See [`PLAN.md`](PLAN.md) for the build order and
[`TODO.md`](TODO.md) for the current step.

## Layout

```
src/police_thief/
  domain/   game rules, board, scoring (not yet implemented)
  infra/    FastMCP server/client, email, LLM provider (not yet implemented)
  peer/     orchestration, handshake, turn handling (not yet implemented)
  shared/   config loading, rate limiting (not yet implemented)
config/
  police/   police's private config + its copy of the shared game.json
  thief/    thief's private config + its copy of the shared game.json
tests/
```

## Running (once implemented)

```
uv sync
uv run pytest
uv run ruff check .
```
