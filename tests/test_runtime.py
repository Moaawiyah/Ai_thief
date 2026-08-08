"""One-game runtime tests with a deterministic Police test double."""

import json
import queue
import threading

from tests.runtime_support import PoliceDouble, QueueTransport
from thief_agent.peer.runtime import ThiefRuntime
from thief_agent.shared.config import ConfigManager


def config(tmp_path, max_moves=3, survival_threshold=2):
    root = tmp_path / "config"
    root.mkdir()
    (root / "game.toml").write_text(
        """
version = "1.10"
[game]
group_id = "thief-team"
group_name = "Thief Team"
members = []
[network]
my_port = 8802
opponent_url = "http://127.0.0.1:8801/mcp"
turn_timeout_seconds = 1
""",
        encoding="utf-8",
    )
    (root / "game.json").write_text(
        json.dumps(
            {
                "schema_version": "1.3",
                "board_and_agents": {"grid_size": 7, "thief_start": [3, 3], "cop_start": [0, 0]},
                "movement_and_barriers": {
                    "max_moves": max_moves,
                    "survival_threshold": survival_threshold,
                    "max_barriers": 14,
                },
            }
        ),
        encoding="utf-8",
    )
    return ConfigManager(root)


def run_pair(tmp_path, scenario="survival"):
    a_to_b, b_to_a = queue.Queue(), queue.Queue()
    cfg = config(tmp_path)
    thief = ThiefRuntime(cfg, QueueTransport(b_to_a, a_to_b))
    police = PoliceDouble(cfg, QueueTransport(a_to_b, b_to_a), scenario)
    results = {}
    threads = [
        threading.Thread(target=lambda: results.setdefault("thief", thief.run())),
        threading.Thread(target=lambda: results.setdefault("police", police.run())),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
        assert not thread.is_alive()
    return results


def test_survival_game_completes_and_audit_passes(tmp_path):
    results = run_pair(tmp_path)
    assert results["thief"]["result"] == "survival"
    assert results["police"]["result"] == "survival"
    assert results["thief"]["audit"]["passed"] is True


def test_capture_claim_completes_and_audit_passes(tmp_path):
    results = run_pair(tmp_path, scenario="capture")
    assert results["thief"]["result"] == "capture"
    assert results["police"]["result"] == "capture"
    assert results["thief"]["audit"]["passed"] is True
