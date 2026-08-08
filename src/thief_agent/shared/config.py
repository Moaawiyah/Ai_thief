"""ConfigManager: loads game.toml + rate_limits.json, validates versions,
serves values via dotted keys with defaults, and overlays the shared
(signed) game.json terms when present.
"""

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

from thief_agent.exceptions import ConfigError, ConfigVersionError
from thief_agent.shared.config_translate import deep_merge, translate_shared
from thief_agent.shared.version import (
    SUPPORTED_CONFIG_VERSIONS,
    SUPPORTED_SHARED_SCHEMA_VERSIONS,
)

__all__ = ["ConfigError", "ConfigVersionError", "ConfigManager"]

GAME_FILE = "game.toml"
RATE_FILE = "rate_limits.json"
SHARED_GAME_FILE = "game.json"


def _check_version(data: dict, source: str) -> None:
    version = data.get("version", "unknown")
    if version not in SUPPORTED_CONFIG_VERSIONS:
        raise ConfigVersionError(
            f"{source} version {version!r} not supported; supported: {SUPPORTED_CONFIG_VERSIONS}"
        )


def _check_shared_schema(data: dict) -> None:
    version = data.get("schema_version", "unknown")
    if version not in SUPPORTED_SHARED_SCHEMA_VERSIONS:
        raise ConfigVersionError(
            "game.json schema version "
            f"{version!r} not supported; supported: {SUPPORTED_SHARED_SCHEMA_VERSIONS}"
        )


class ConfigManager:
    """Load one private Thief directory and expose dotted-key access."""

    def __init__(self, config_dir: str | Path):
        self.directory = Path(config_dir)
        if not self.directory.is_dir():
            raise ConfigError(f"Config directory not found: {self.directory}")
        self._data = self._read_toml(self.directory / GAME_FILE)
        self._rates = self._read_json(self.directory / RATE_FILE, required=False)
        _check_version(self._data, GAME_FILE)
        if self._rates:
            _check_version(self._rates, RATE_FILE)
        # Optional shared, agreed game terms (JSON). When present it overlays the
        # local TOML game-terms, so both peers play byte-identical agreed rules.
        shared_path = self.directory / SHARED_GAME_FILE
        if shared_path.is_file():
            raw = shared_path.read_bytes()
            shared = self._read_json(shared_path, required=True)
            _check_shared_schema(shared)
            deep_merge(self._data, translate_shared(shared))
            self.shared = shared
            self._shared_sha256 = hashlib.sha256(raw).hexdigest()
        else:
            self.shared = {}
            self._shared_sha256 = ""

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
    def _read_json(path: Path, *, required: bool) -> dict:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            if required:
                raise ConfigError(f"Missing config file: {path}") from None
            return {}
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigError(f"Configuration must be an object: {path}")
        return data

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Fetch a game.toml value by dotted key, e.g. 'board.size'."""
        node: Any = self._data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def require(self, dotted_key: str) -> Any:
        """Return a required setting or raise an error naming its dotted key."""
        value = self.get(dotted_key)
        if value is None:
            raise ConfigError(f"Missing required config key {dotted_key!r}")
        return value

    def override(self, dotted_key: str, value: Any) -> None:
        """Set a value by dotted key (e.g. live GUI sub-game overrides)."""
        parts = dotted_key.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    @property
    def rate_limits(self) -> dict:
        """The full rate_limits.json contents (empty dict if none present)."""
        return self._rates

    @property
    def shared_sha256(self) -> str:
        """SHA-256 of the exact shared game.json bytes used by this peer."""
        return self._shared_sha256

    def service_limits(self, service: str) -> dict:
        """Rate limits for a service, falling back to the default block."""
        return self._rates.get("services", {}).get(service) or self._rates.get("default", {})
