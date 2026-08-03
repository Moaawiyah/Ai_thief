"""Public SDK composition and persistence behavior."""

import json
import queue

import pytest

from tests.runtime_support import QueueTransport
from tests.test_runtime import config
from thief_agent.sdk import MatchOptions, ThiefAgentSDK
from thief_agent.shared.config import ConfigError


def test_sdk_resolves_settings_and_keeps_injected_transport(tmp_path):
    transport = QueueTransport(queue.Queue(), queue.Queue())
    agent = ThiefAgentSDK(
        MatchOptions(host="0.0.0.0", port=9001, opponent_url="http://other/mcp"),
        config=config(tmp_path),
        transport=transport,
    )

    assert (agent.host, agent.port, agent.opponent_url) == (
        "0.0.0.0",
        9001,
        "http://other/mcp",
    )
    assert agent.connect() is transport


def test_sdk_runtime_is_lazy_but_stable(tmp_path):
    transport = QueueTransport(queue.Queue(), queue.Queue())
    agent = ThiefAgentSDK(config=config(tmp_path), transport=transport)

    assert agent.runtime is agent.runtime


def test_sdk_saves_and_loads_the_full_summary(tmp_path):
    transport = QueueTransport(queue.Queue(), queue.Queue())
    agent = ThiefAgentSDK(config=config(tmp_path), transport=transport)
    path = agent.save_summary({"role": "thief", "steps": 2}, tmp_path / "result.json")

    assert json.loads(path.read_text()) == {"role": "thief", "steps": 2}
    assert agent.load_summary(path)["role"] == "thief"


def test_sdk_names_missing_logs_clearly(tmp_path):
    agent = ThiefAgentSDK(config=config(tmp_path), transport=object())

    with pytest.raises(ConfigError, match="Match log not found"):
        agent.load_summary(tmp_path / "missing.json")
