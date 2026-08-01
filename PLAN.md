# Development Plan

Incremental build order (per CLAUDE.md). Each step must be implemented,
tested, and verified against the specification before moving to the next.

1. **Project setup** — `uv` project, Ruff/pytest/coverage config, package
   skeleton, config separation. *(this step)*
2. Core game/domain rules — board, movement, barriers, scoring, win
   conditions (spec ch. 1, 3).
3. Local playable simulation — both brains running in-process against each
   other, no networking yet.
4. P2P/FastMCP communication — real two-process peer connection (spec ch. 2).
5. Commit-reveal/security — signed moves, SHA-256, nonce anti-replay (spec
   ch. 5).
6. Scent and belief system — pheromone emission/decay, Bayesian belief map
   (spec ch. 4, 6).
7. Police/Thief strategies — decoupled from rules engine (spec ch. 6).
8. GUI, replay, and reporting — live heatmap, replay viewer, mandatory
   Gmail report (spec ch. 7, 9).
9. Final integration and interoperability testing — league play against
   another student's implementation.

Do not implement future steps ahead of schedule.
