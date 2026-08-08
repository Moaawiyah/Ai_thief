"""Protocol state coverage and provider adapters with external calls mocked."""

import json
from types import SimpleNamespace

import pytest

from thief_agent.domain.actions import move
from thief_agent.domain.hint_state import projected_hint_state
from thief_agent.domain.own_state import OwnGameState
from thief_agent.domain.state_machine import MatchState, ProtocolStateMachine
from thief_agent.exceptions import (
    ConfigError,
    ProtocolStateError,
    ProviderCliError,
    ProviderError,
    ProviderParseError,
)
from thief_agent.infra.llm_provider import ClaudeCliProvider
from thief_agent.infra.ollama import OllamaAsker
from thief_agent.infra.ollama_provider import OllamaLlmProvider
from thief_agent.sdk.provider_factory import build_llm
from thief_agent.sdk.providers import StubLlm


class Config:
    rate_limits = {"services": {}, "queue": {
        "max_depth": 3, "drain_interval_seconds": 0, "timeout_seconds": 1
    }}

    def __init__(self, **values):
        self.values = values

    def get(self, key, default=None):
        return self.values.get(key, default)

    def service_limits(self, name):
        return {"requests_per_minute": 100, "concurrent_max": 1, "max_retries": 0,
                "daily_quota": 100}


class Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.body).encode()


class InvalidJsonResponse(Response):
    def read(self):
        return b"{bad"


def test_state_machine_and_projected_hint_state_cover_terminal_paths():
    machine = ProtocolStateMachine()
    machine.transition_match(MatchState.NEGOTIATING)
    machine.transition_match(MatchState.STEP_ZERO)
    machine.local_turn()
    machine.verified_incoming()
    machine.technical_loss()
    with pytest.raises(ProtocolStateError):
        machine.transition_match(MatchState.FINISHED)
    state = OwnGameState((3, 3), 7)
    assert projected_hint_state(state, None, None).position == (3, 3)
    state.apply_move(move(state.board.legal_moves(state.position, set())[0][0]))
    assert projected_hint_state(state, None, None).position == state.position


def test_ollama_adapters_parse_usage_and_fail_cleanly(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: Response({"response": "ok", "prompt_eval_count": 2,
                                            "eval_count": 3}),
    )
    asker = OllamaAsker("model", "http://ollama", 1)
    assert asker("prompt") == "ok"
    assert asker.tokens_consumed == 5
    provider = OllamaLlmProvider(Config(**{"llm.model": "model", "llm.ollama_url": "http://x"}))
    assert provider.send("p") == "ok"

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response({}))
    with pytest.raises(ProviderError):
        asker("prompt")
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: InvalidJsonResponse("bad"))
    with pytest.raises(ProviderParseError):
        provider.send("p")


def test_claude_provider_extracts_usage_and_strips_credentials(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "thief_agent.infra.llm_provider.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="claude 1", stderr=""),
    )
    config = Config(**{"llm.executable": "claude", "llm.args": ["-p"],
                       "llm.model": "model", "llm.timeout_seconds": 2})
    provider = ClaudeCliProvider(config)
    assert provider._extract(json.dumps({"result": "```json\nanswer\n```", "usage": {
        "input_tokens": 2, "output_tokens": 4}})) == "answer"
    assert provider.tokens_consumed == 6
    seen = {}

    def run(*args, **kwargs):
        seen.update(kwargs)
        return SimpleNamespace(returncode=0, stdout=json.dumps({"result": "ok"}), stderr="")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    monkeypatch.setattr("thief_agent.infra.llm_provider.subprocess.run", run)
    assert provider._run("claude", 1)
    assert "ANTHROPIC_API_KEY" not in seen["env"]
    monkeypatch.setattr(
        "thief_agent.infra.llm_provider.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="bad"),
    )
    with pytest.raises(ProviderCliError):
        provider._run("claude", 1)


def test_provider_factory_returns_stub_and_rejects_unknown_provider():
    stub = build_llm(Config())
    assert isinstance(stub, StubLlm)
    assert stub.send("anything")
    with pytest.raises(ConfigError, match="llm.provider"):
        build_llm(Config(**{"llm.provider": "unknown"}))
