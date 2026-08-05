"""Self-documenting `_schema`/`_remark` text for the four game JSON artifacts,
matching the reference peer's Json-examples/ templates (assignment Appendix F).
"""

SCHEMA_VERSION = "1.1"
DEFAULT_TIMEZONE = "Asia/Jerusalem"

SCHEMA_DECLARATION = "Static declaration for the WHOLE game (the full series of sub-games) between two teams. This is the single home for every field that does NOT change while the sub-games are played: team identity, members, cop/thief repository URLs, MCP server URLs, hardware spec, LLM model, the agreed max-tokens-per-game cap, and the game start/end times. Roles (cop/thief) switch across the sub-games, so no role and no sub_game_number appear here. Both teams sign it and lock it cryptographically before play. Data that changes per sub-game (github_commit, moves, scores) lives in 3-game-log.json and 4-final-result.json."

SCHEMA_CONFIG = "Agreed game configuration for one match. Values come from the master parameter table (Appendix F). Both teams must hold BYTE-IDENTICAL values, lock them cryptographically (config_sha256), give the file a unique name per game, and attach it to GitHub."

SCHEMA_LOG = "Per-sub-game match log consumed by the Replay Viewer for cryptographic audit. Each step is committed as SHA-256(canonical_payload || nonce) and later revealed; nonces are revealed only at the final audit. Static team metadata (hardware, members, repos, model) is NOT repeated here — it lives in 1-pre-game-declaration.json; join by game_uid. The 'prompt_discussion' block records the strategy reasoning behind each move and hint."

SCHEMA_RESULT = "Summary and final result for the WHOLE game (all sub-games) between two teams. It condenses the per-sub-game logs into a per-group score for every sub-game plus the aggregate outcome. Static team metadata (identity, members, repos, MCP, hardware, model) is NOT repeated here — it lives in 1-pre-game-declaration.json and is referenced via game_id / group_id. Both teams must agree on this result."

LINKS_REMARK = "These are logical roles, NOT fixed filenames. Each actual file name MUST be derived from the game_id so that files from different games are never mixed. Match-level files (declaration, result) are named <role>_<game_id>.json; per-sub-game files (config, log) are named <role>_<game_id>_g<NN>.json where <NN> is the sub_game_number."
