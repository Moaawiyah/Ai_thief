# Thief Development Plan

This repository implements the Thief peer. The Police peer is maintained in
`https://github.com/Moaawiyah/police-agent.git`. Shared domain and protocol
files must remain compatible between the two repositories.

Incremental build order (per CLAUDE.md). Each step must be implemented,
tested, and verified against the specification before moving to the next.

1. **Project setup** — `uv` project, Ruff/pytest/coverage config, package
   skeleton, config separation. *(this step)*
2. Core game/domain rules — board, movement, barriers, scoring, win
   conditions (spec ch. 1, 3).
3. Local playable simulation — the Thief brain running against a local test
   double, no networking yet.
4. P2P/FastMCP communication — real two-process peer connection (spec ch. 2).
5. Commit-reveal/security — signed moves, SHA-256, nonce anti-replay (spec
   ch. 5).
6. Scent and belief system — pheromone emission/decay, Bayesian belief map
   (spec ch. 4, 6). *(implemented)*
7. Thief strategy — decoupled from the shared rules engine (spec ch. 6).
8. GUI, replay, and reporting — live heatmap, replay viewer, mandatory
   Gmail report (spec ch. 7, 9).
9. Final integration and interoperability testing — league play against
   another student's implementation.

Do not implement future steps ahead of schedule.
