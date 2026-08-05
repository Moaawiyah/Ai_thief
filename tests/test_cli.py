"""CLI dispatch tests without starting a real long-lived server."""

import json

import pytest

import thief_agent
from thief_agent.shared.config import ConfigError


def test_play_dispatches_to_runtime(monkeypatch, capsys):
    class FakeConfig:
        def __init__(self, directory):
            self.directory = directory

        def override(self, key, value):
            setattr(self, key.replace(".", "_"), value)

    class FakeRuntime:
        def __init__(self, config):
            self.config = config

        def run(self):
            return {"result": "survival"}

    monkeypatch.setattr("thief_agent.shared.config.ConfigManager", FakeConfig)
    monkeypatch.setattr("thief_agent.peer.runtime.ThiefRuntime", FakeRuntime)
    thief_agent.main(["play", "--config-dir", "demo", "--port", "9900"])

    assert json.loads(capsys.readouterr().out)["result"] == "survival"


def test_server_dispatches_to_fastmcp(monkeypatch):
    calls = []

    class FakeServer:
        def run(self, **kwargs):
            calls.append(kwargs)

    class FakeInboxes:
        pass

    monkeypatch.setattr(
        "thief_agent.infra.mcp_server.build_peer_server",
        lambda role, inboxes: FakeServer(),
    )
    monkeypatch.setattr("thief_agent.infra.mcp_server.PeerInboxes", FakeInboxes)
    thief_agent.main(["server", "--host", "0.0.0.0", "--port", "9901"])
    assert calls == [
        {
            "transport": "http",
            "host": "0.0.0.0",
            "port": 9901,
            "show_banner": False,
            "log_level": "warning",
        }
    ]


def test_main_requires_a_subcommand():
    with pytest.raises(SystemExit):
        thief_agent.main([])


def test_play_reports_missing_config(monkeypatch):
    class MissingConfig:
        def __init__(self, directory):
            raise ConfigError("missing private configuration")

    monkeypatch.setattr("thief_agent.shared.config.ConfigManager", MissingConfig)
    with pytest.raises(SystemExit):
        thief_agent.main(["play", "--config-dir", "missing"])
