"""Private TOML plus shared JSON configuration loading."""

import json
import tomllib
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when the local or shared configuration is missing or invalid."""


def _deep_merge(base: dict, overlay: dict) -> None:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _shared_overlay(shared: dict) -> dict:
    board = shared.get("board_and_agents", {})
    movement = shared.get("movement_and_barriers", {})
    pheromones = shared.get("pheromones", {})
    network = shared.get("network_and_league", {})
    world = shared.get("world", {})
    return {
        "board": {
            "size": board.get("grid_size"),
            "axis_origin_corner": board.get("axis_origin_corner", "top-left"),
            "axis_start_index": board.get("axis_start_index", 0),
        },
        "positions": {
            "thief_start": board.get("thief_start"),
            "cop_start": board.get("cop_start"),
        },
        "play": {
            "setting": world.get("map_area", ""),
            "hint_max_words": world.get("hint_max_words", 15),
        },
        "rules": {
            "move_set": movement.get("move_set", ["N", "S", "E", "W", "STAY"]),
            "barriers_max": movement.get("max_barriers", 0),
            "max_steps": movement.get("max_moves"),
            "survival_threshold": movement.get("survival_threshold"),
        },
        "smell": {
            "grid_size": pheromones.get("pheromone_grid_size", 5),
            "decay_per_step": pheromones.get("pheromone_decay", 0.1),
            "emit_intensity": pheromones.get("pheromone_center_intensity", 0.9),
            "min_center_intensity": pheromones.get("pheromone_min_center_intensity", 0.5),
        },
        "network": {
            "turn_timeout_seconds": network.get("response_timeout_sec", 30),
        },
        "game": {"num_games": network.get("num_games", 1)},
        "scoring": shared.get("scoring", {}),
    }


class ConfigManager:
    """Load one private Thief directory and expose dotted-key access."""

    def __init__(self, config_dir: str | Path):
        self.directory = Path(config_dir)
        if not self.directory.is_dir():
            raise ConfigError(f"Config directory not found: {self.directory}")
        self._data = self._read_toml(self.directory / "game.toml")
        shared_path = self.directory / "game.json"
        if not shared_path.is_file():
            raise ConfigError(f"Missing shared game configuration: {shared_path}")
        shared = self._read_json(shared_path)
        _deep_merge(self._data, _shared_overlay(shared))
        self.shared = shared

    @staticmethod
    def _read_toml(path: Path) -> dict:
        try:
            with path.open("rb") as handle:
                return tomllib.load(handle)
        except FileNotFoundError as exc:
            raise ConfigError(f"Missing private configuration: {path}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc

    @staticmethod
    def _read_json(path: Path) -> dict:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise ConfigError(f"Invalid or missing shared JSON: {path}") from exc
        if not isinstance(data, dict):
            raise ConfigError(f"Shared configuration must be an object: {path}")
        return data

    def get(self, dotted_key: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def override(self, dotted_key: str, value: Any) -> None:
        parts = dotted_key.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
