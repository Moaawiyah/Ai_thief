# TODO

## Step 1 — Project setup (done)

- [x] `uv init`, `pyproject.toml` deps (fastmcp, pytest, pytest-cov, ruff)
- [x] Ruff / pytest / coverage config (85% fail-under)
- [x] `src/police_thief/{domain,infra,peer,shared}` empty package skeleton
- [x] `config/police/`, `config/thief/` separation with shared `game.json`
      and private `game.toml.example`
- [x] Smoke test, `.gitignore`, README/PLAN/TODO stubs

## Step 2 — Core game/domain rules (done)

- [x] `constants.py`: `Role`, `MoveType`, `Direction` (N/S/E/W only), `DELTAS`
- [x] `domain/board.py`: bounds, orthogonal steps, `legal_moves`,
      `barrier_targets` (own cell + 4 neighbours, per spec 3.4)
- [x] `domain/actions.py`: validated `Action` value object
- [x] `domain/own_state.py`: per-peer state, `apply_move`, barrier quota,
      `is_confined`
- [x] `domain/rules.py`: survival threshold, capture claim, `barrier_captures`
      (Appendix ה #46), `confinement_capture` (Appendix ה #47)
- [x] `domain/scoring.py`: scoring table + series tie rule
- [x] Tests: 61 passing, 99% coverage, zero Ruff violations

## Step 3 — Local playable simulation (next)

- [ ] Read `config/*/game.json` into the domain layer (shared terms only)
- [ ] Drive two `OwnGameState` peers through a turn loop in one process
- [ ] Scripted/random move selection only — real strategy is step 7
