"""Translate the signed Appendix-F JSON into the application's dotted namespace."""

from typing import Any


def _put(out: dict, section: str, key: str, value: Any) -> None:
    """Store one translated value, creating its section when needed."""
    out.setdefault(section, {})[key] = value


def translate_shared(shared: dict) -> dict:
    """Return the internal configuration overlay represented by shared JSON terms.

    Field names mirror the Police peer's translator where the underlying concept
    is the same, but movement/steps stay Thief-specific: `max_moves` feeds
    `rules.max_steps` and `survival_threshold` feeds its own `rules.survival_threshold`
    (the Thief brain tracks both end-conditions independently; Police's rules
    collapse them into one).
    """
    out: dict[str, dict] = {}
    board = shared.get("board_and_agents", {})
    board_keys = {
        "grid_size": ("board", "size"),
        "thief_start": ("positions", "thief_start"),
        "cop_start": ("positions", "cop_start"),
        "axis_origin_corner": ("board", "axis_origin_corner"),
        "axis_start_index": ("board", "axis_start_index"),
    }
    for source, (section, target) in board_keys.items():
        if source in board:
            _put(out, section, target, board[source])

    world = shared.get("world", {})
    for source, target in (("map_area", "setting"), ("hint_max_words", "hint_max_words")):
        if source in world:
            _put(out, "play", target, world[source])

    movement = shared.get("movement_and_barriers", {})
    movement_keys = {
        "move_set": "move_set",
        "max_barriers": "barriers_max",
        "max_moves": "max_steps",
        "survival_threshold": "survival_threshold",
    }
    for source, target in movement_keys.items():
        if source in movement:
            _put(out, "rules", target, movement[source])

    if "scoring" in shared:
        out["scoring"] = dict(shared["scoring"])

    pheromones = shared.get("pheromones", {})
    scent_keys = {
        "pheromone_center_intensity": "emit_intensity",
        "pheromone_decay": "decay_per_step",
        "pheromone_grid_size": "grid_size",
        "pheromone_min_center_intensity": "min_center_intensity",
    }
    for source, target in scent_keys.items():
        if source in pheromones:
            _put(out, "smell", target, pheromones[source])

    league = shared.get("network_and_league", {})
    if "num_games" in league:
        _put(out, "game", "num_games", league["num_games"])
    if "response_timeout_sec" in league:
        _put(out, "network", "turn_timeout_seconds", league["response_timeout_sec"])
        _put(out, "network", "response_timeout_seconds", league["response_timeout_sec"])
    if "watchdog_timeout_sec" in league:
        _put(out, "network", "watchdog_timeout_seconds", league["watchdog_timeout_sec"])

    strategy = shared.get("strategy_agreement", {})
    strategy_keys = {
        "llm_tactics_allowed": "llm_tactics_allowed",
        "contract_version": "llm_contract_version",
    }
    for source, target in strategy_keys.items():
        if source in strategy:
            _put(out, "strategy", target, strategy[source])
    return out


def deep_merge(base: dict, overlay: dict) -> None:
    """Recursively merge ``overlay`` into ``base``."""
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
