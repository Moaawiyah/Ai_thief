"""Constrained LLM tactics: fallback safety and the resolve_brain factory."""

import pytest

from thief_agent.constants import Direction, MoveType
from thief_agent.domain.belief import BeliefGrid
from thief_agent.domain.own_state import OwnGameState
from thief_agent.exceptions import ConfigError
from thief_agent.strategy import ThiefBrain, resolve_brain
from thief_agent.strategy.llm_tactics import LlmTactics
from thief_agent.strategy.team_strategy import MobilityThiefBrain


class _BadLlm:
    def send(self, prompt, timeout=None, schema=None):
        return "not json"


class _GoodLlm:
    def __init__(self, action_id):
        self._action_id = action_id

    def send(self, prompt, timeout=None, schema=None):
        import json

        return json.dumps({"action_id": self._action_id, "confidence": 0.9, "reasoning": "test"})


class _FakeConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def test_invalid_llm_reply_falls_back_to_the_heuristic_move():
    state = OwnGameState(start=(3, 3), board_size=7)
    belief = BeliefGrid(7)
    tactics = LlmTactics(_FakeConfig(), _BadLlm())

    choice = tactics.choose(state, belief, MoveType.MOVE, Direction.N)

    assert choice.source == "heuristic_fallback"
    assert choice.fallback_reason == "invalid_json"
    assert choice.move_type is MoveType.MOVE
    assert choice.direction is Direction.N


def test_valid_llm_reply_selects_the_named_candidate():
    state = OwnGameState(start=(3, 3), board_size=7)
    belief = BeliefGrid(7)
    tactics = LlmTactics(_FakeConfig(), _GoodLlm("A0"))

    choice = tactics.choose(state, belief, MoveType.HOLD, None)

    assert choice.source == "llm"
    assert choice.action_id == "A0"


def test_resolve_brain_defaults_to_the_shipped_heuristic():
    brain = resolve_brain(_FakeConfig())
    assert isinstance(brain, ThiefBrain)


def test_resolve_brain_honours_the_dotted_selector():
    brain = resolve_brain(
        _FakeConfig(
            **{"strategy.thief_class": "thief_agent.strategy.team_strategy:MobilityThiefBrain"}
        )
    )
    assert isinstance(brain, MobilityThiefBrain)


def test_resolve_brain_rejects_llm_mode_without_consent():
    with pytest.raises(ConfigError, match="mutual signed consent"):
        resolve_brain(_FakeConfig(**{"strategy.mode": "llm"}), llm=_GoodLlm("A0"))


def test_resolve_brain_enables_tactics_when_agreed():
    config = _FakeConfig(
        **{
            "strategy.mode": "llm",
            "strategy.llm_tactics_allowed": True,
            "strategy.llm_contract_version": "1.0",
        }
    )
    brain = resolve_brain(config, llm=_GoodLlm("A0"))
    assert brain._tactics is not None
