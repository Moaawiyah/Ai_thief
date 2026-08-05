"""Sealing helpers: build and SHA-256-seal the records this peer commits to —
the per-step state payloads and the one-time host-spec declaration.
"""

from datetime import UTC, datetime

from thief_agent.domain.crypto import CommitReveal
from thief_agent.exceptions import ConfigError
from thief_agent.peer.step_records import (
    build_terminal_message as build_terminal_message,
)
from thief_agent.peer.step_records import (
    build_turn_message as build_turn_message,
)
from thief_agent.peer.step_records import sealed_step_record as sealed_step_record
from thief_agent.shared.git_info import code_revision
from thief_agent.shared.sysinfo import collect_spec
from thief_agent.shared.version import CODE_VERSION

__all__ = [
    "REQUIRED_TERMS",
    "now_iso",
    "sealed_spec_record",
    "identity_from_config",
    "terms_from_config",
    "validate_agreement",
    "validate_config",
    "build_turn_message",
    "build_terminal_message",
]

# Agreed terms with NO code default: they must resolve (from the shared game.json)
# or the game would crash mid-play on a None.
REQUIRED_TERMS = (
    "board_size",
    "smell_grid_size",
    "decay_per_step",
    "emit_intensity",
    "min_center_intensity",
    "max_steps",
    "barriers_max",
    "thief_start",
    "cop_start",
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def sealed_spec_record(config, sub_game_number: int = 1) -> dict:
    """Host spec + model + group identity + code version, sealed (step 0)."""
    payload = {
        "step": 0,
        "type": "system_spec",
        "spec": collect_spec(),
        "model": config.get("llm.model", "") or "cli-default",
        "code_version": CODE_VERSION,
        "github_commit": code_revision()["commit"],
        "working_tree_dirty": code_revision()["dirty"],
        "group_name": config.get("game.group_name", "unnamed"),
        "sub_game_number": sub_game_number,
    }
    return {"payload": payload, **CommitReveal.seal(payload)}


def identity_from_config(config) -> dict:
    """This peer's static group identity, exchanged in the handshake."""
    return {
        "group_id": config.get("game.group_id", "unknown-group"),
        "group_name": config.get("game.group_name", "unnamed"),
        "members": config.get("game.members", []),
        "repos": config.get("game.repos", {}),
        "mcp_servers": config.get("game.mcp_servers", {}),
        "llm_model": config.get("llm.model", "") or "cli-default",
        "llm_provider": config.get("llm.provider", "template"),
        "strategy_mode": config.get("strategy.mode", "heuristic"),
        "spec": collect_spec(),
        "github_commit": code_revision()["commit"],
        "working_tree_dirty": code_revision()["dirty"],
    }


def terms_from_config(config) -> dict:
    """The signed game agreement: everything both peers MUST match on.

    `llm_tactics_allowed`, `llm_contract_version` and `config_sha256` are
    deliberately NOT here: they are this peer's own local settings/derived
    values, not something the Police peer's terms dict is built to match, and
    the handshake fails on any key present on one side and absent on the
    other even when every shared value agrees (`domain/negotiation.py`).
    """
    return {
        "board_size": config.get("board.size"),
        "smell_grid_size": config.get("smell.grid_size", 5),
        "decay_per_step": config.get("smell.decay_per_step", 0.1),
        "emit_intensity": config.get("smell.emit_intensity", 0.9),
        "min_center_intensity": config.get("smell.min_center_intensity", 0.5),
        "max_steps": config.get("rules.max_steps"),
        "barriers_max": config.get("rules.barriers_max"),
        "setting": config.get("play.setting", ""),
        "hint_max_words": config.get("play.hint_max_words", 15),
        "axis_origin_corner": config.get("board.axis_origin_corner", "top-left"),
        "axis_start_index": config.get("board.axis_start_index", 0),
        "thief_start": config.get("positions.thief_start"),
        "cop_start": config.get("positions.cop_start"),
        "num_games": config.get("game.num_games", 1),
    }


def validate_agreement(config) -> None:
    """Fail fast (before any server/port is opened) if a required agreed term is
    missing, and — when LLM tactics are turned on locally — that this peer's own
    config carries the signed contract version. Not agreed terms: local-only."""
    terms = terms_from_config(config)
    missing = [name for name in REQUIRED_TERMS if terms.get(name) is None]
    if missing:
        raise ConfigError(
            "Missing required agreed game term(s): " + ", ".join(missing) + ". "
            "These are SHARED terms that must be declared in this peer's game.json. "
            "Make sure config/thief/game.json exists and is complete."
        )
    if str(config.get("strategy.mode", "heuristic")).lower() == "llm":
        if not config.get("strategy.llm_tactics_allowed", False):
            raise ConfigError("LLM tactics require mutual signed consent in game.json")
        if config.get("strategy.llm_contract_version", "") != "1.0":
            raise ConfigError("LLM tactics require signed contract_version '1.0'")
    shared = getattr(config, "shared", None)
    if shared:
        from thief_agent.shared.agreement import validate_shared_config

        validate_shared_config(shared)


def validate_config(config) -> None:
    """Backward-compatible network/board sanity check (pre-agreement wiring)."""
    required = {
        "board.size": config.get("board.size"),
        "rules.max_steps": config.get("rules.max_steps"),
        "rules.survival_threshold": config.get("rules.survival_threshold"),
        "positions.thief_start": config.get("positions.thief_start"),
        "positions.cop_start": config.get("positions.cop_start"),
        "network.opponent_url": config.get("network.opponent_url"),
        "network.my_port": config.get("network.my_port"),
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ConfigError("Missing required configuration: " + ", ".join(missing))
