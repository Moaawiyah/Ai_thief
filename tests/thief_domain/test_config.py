"""Tests for private TOML plus shared game JSON loading."""

import json

import pytest

from thief_agent.exceptions import ConfigVersionError
from thief_agent.shared.config import ConfigError, ConfigManager

TOML = """
version = "1.10"
[game]
group_id = "thief-team"
group_name = "Thief Team"
[network]
my_port = 8802
opponent_url = "http://127.0.0.1:8801/mcp"
"""


def write_config(root):
    root.mkdir()
    (root / "game.toml").write_text(TOML, encoding="utf-8")
    (root / "game.json").write_text(
        json.dumps(
            {
                "board_and_agents": {
                    "grid_size": 7,
                    "thief_start": [3, 3],
                    "cop_start": [0, 0],
                },
                "movement_and_barriers": {"max_moves": 3, "survival_threshold": 2},
            }
        ),
        encoding="utf-8",
    )


def test_shared_json_overlays_dotted_values(tmp_path):
    root = tmp_path / "thief"
    write_config(root)
    config = ConfigManager(root)
    assert config.get("board.size") == 7
    assert config.get("positions.thief_start") == [3, 3]
    assert config.get("rules.max_steps") == 3
    assert config.get("network.my_port") == 8802


def test_missing_private_toml_is_clear(tmp_path):
    root = tmp_path / "thief"
    root.mkdir()
    (root / "game.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ConfigError, match="private configuration"):
        ConfigManager(root)


def test_missing_shared_json_is_optional(tmp_path):
    """Mirrors the Police peer: the shared overlay is optional-but-preferred,
    so a peer can still boot from private config alone (e.g. local dev)."""
    root = tmp_path / "thief"
    root.mkdir()
    (root / "game.toml").write_text(TOML, encoding="utf-8")
    config = ConfigManager(root)
    assert config.shared == {}
    assert config.shared_sha256 == ""
    assert config.get("network.my_port") == 8802


def test_unsupported_config_version_is_rejected(tmp_path):
    root = tmp_path / "thief"
    write_config(root)
    (root / "game.toml").write_text(TOML.replace('"1.10"', '"0.1"'), encoding="utf-8")
    with pytest.raises(ConfigVersionError):
        ConfigManager(root)


def test_shared_sha256_reflects_exact_bytes(tmp_path):
    root = tmp_path / "thief"
    write_config(root)
    config = ConfigManager(root)
    assert config.shared_sha256
    assert len(config.shared_sha256) == 64


def test_missing_directory_is_clear(tmp_path):
    with pytest.raises(ConfigError, match="directory not found"):
        ConfigManager(tmp_path / "missing")
