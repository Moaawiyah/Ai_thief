# Thief TODO

This repository owns the Thief peer. Keep shared rule/config changes aligned
with `https://github.com/Moaawiyah/police-agent.git`.

## Step 1 — Project setup (done)

- [x] `uv init`, `pyproject.toml` deps (fastmcp, pytest, pytest-cov, ruff)
- [x] Ruff / pytest / coverage config (85% fail-under)
- [x] `src/thief_agent/{domain,infra,peer,shared}` package skeleton
- [x] Thief-only `config/thief/` with shared `game.json` and private
      `game.toml.example`
- [x] Smoke test, `.gitignore`, README/PLAN/TODO stubs

## Step 2 — Core game/domain rules (done)

- [x] `constants.py`: Thief `MoveType`, `Direction` (N/S/E/W only), `DELTAS`
- [x] `domain/board.py`: bounds, orthogonal steps, `legal_moves`, and
      observed-barrier blocking
- [x] `domain/actions.py`: validated Thief `Action` value object
- [x] `domain/own_state.py`: Thief position, movement history, and observed
      barriers; no Police-owned barrier placement
- [x] `domain/rules.py`: Thief survival, capture claims, barrier capture
      (Appendix ה #46), and confinement capture (Appendix ה #47)
- [x] `domain/scoring.py`: scoring table + series tie rule
- [x] Tests: 61 passing, 99% coverage, zero Ruff violations

## Step 3 — Thief local playable simulation (done)

- [x] Adopt the reference-style pure-Python `ThiefBrain` with legal-move and
      unvisited-cell selection
- [x] Add a Thief-side belief grid for the unseen Police position
- [x] Read `config/thief/game.json` into the runtime configuration layer
- [x] Drive the Thief `OwnGameState` against a deterministic Police test double
- [x] Scripted/random Thief move selection only — real strategy is step 7

## Step 4 — FastMCP transport and one-game runtime (done)

- [x] Start an independent FastMCP HTTP mailbox for the Thief peer
- [x] Send and poll agreements, turns, and audit payloads through the opponent URL
- [x] Verify a real two-port FastMCP round trip
- [x] Add the signed peer handshake and turn orchestration
- [x] Add validated turn/audit/control wire models
- [x] Add SHA-256 commit-reveal sealing and audit verification
- [x] Add `thief-agent server` and `thief-agent play` subcommands
- [x] Verify a complete one-game exchange over real FastMCP HTTP

## Step 5 — Follow-up

- [ ] Add full pheromone emission/decay and belief fusion
- [ ] Add multi-game series aggregation and role alternation
- [ ] Add reporting artifacts, replay, and GUI integration
