# TODO

## Step 1 — Project setup (done)

- [x] `uv init`, `pyproject.toml` deps (fastmcp, pytest, pytest-cov, ruff)
- [x] Ruff / pytest / coverage config (85% fail-under)
- [x] `src/police_thief/{domain,infra,peer,shared}` empty package skeleton
- [x] `config/police/`, `config/thief/` separation with shared `game.json`
      and private `game.toml.example`
- [x] Smoke test, `.gitignore`, README/PLAN/TODO stubs

## Step 2 — Core game/domain rules (next)

- [ ] `domain/board.py`: grid, barrier placement, legal-move checks
- [ ] `domain/rules.py`: movement validation, capture-claim adjacency check
- [ ] `domain/scoring.py`: scoring table from `config/*/game.json`
- [ ] Tests for all of the above
