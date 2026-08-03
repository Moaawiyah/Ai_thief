"""Caller-controlled settings for one Thief match."""

from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_DIR = "config/thief"
DEFAULT_HOST = "127.0.0.1"


@dataclass(frozen=True)
class MatchOptions:
    """Settings collected by a CLI, GUI, or another Python caller."""

    config_dir: str | Path = DEFAULT_CONFIG_DIR
    host: str = DEFAULT_HOST
    port: int | None = None
    opponent_url: str | None = None
