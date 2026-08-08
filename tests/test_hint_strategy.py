"""Grounded hint selection and optional provider routing."""

import json
import random
from types import SimpleNamespace

from thief_agent.constants import MoveType
from thief_agent.domain.belief import BeliefGrid
from thief_agent.domain.brains import Decision
from thief_agent.domain.own_state import OwnGameState
from thief_agent.peer.turn_sender import _write_hint
from thief_agent.strategy.hint_candidates import ranked_hint_candidates
from thief_agent.strategy.hint_prompt import build_hint_prompt
from thief_agent.strategy.llm_hints import LlmTrashTalk
from thief_agent.strategy.talk import asker_from_config, resolve_hint_writer
from thief_agent.strategy.talk_providers import resolve_trash_talk
from thief_agent.strategy.team_strategy import MobilityThiefBrain
from thief_agent.strategy.trash_talk import TrashTalk


class Config:
    def __init__(self, **values):
        self.values = values

    def get(self, key, default=None):
        return self.values.get(key, default)


def test_grounded_candidates_and_prompt_are_coordinate_aware():
    state, belief = OwnGameState((3, 3), 7), BeliefGrid(7)
    candidates = ranked_hint_candidates(state, belief, "New York")
    system, user = build_hint_prompt(state, belief, candidates, 15)
    assert len(candidates) == 5
    assert candidates[0].prompt_value()["action_id"] == "H0"
    assert "opponent_hint_omitted_as_untrusted" in user
    assert "north while" in system
    assert "coordinates" in system


def test_llm_hint_accepts_grounded_json_and_falls_back_on_bad_reply():
    state, belief = OwnGameState((3, 3), 7), BeliefGrid(7)
    candidates = ranked_hint_candidates(state, belief, "London")
    reply = json.dumps({
        "action_id": "H0", "message": candidates[0].fallback_message,
        "confidence": 0.9, "reasoning": "lure",
    })
    good = LlmTrashTalk(lambda *_: reply, random.Random(0))
    assert good.say(state, belief, "London", "")[1] == candidates[0].verdict
    bad = LlmTrashTalk(lambda *_: "not json", random.Random(0))
    result = bad.say(state, belief, "London", "")
    assert result[0] and bad.last_source == "grounded_fallback"
    assert bad.tokens_consumed == 0


def test_template_and_simple_hint_resolvers_are_safe():
    template = TrashTalk(random.Random(0), max_words=3)
    assert len(template.say(None, None, "Paris", "")[0].split()) <= 3
    writer = resolve_hint_writer(Config(**{"trash_talk.provider": "template"}), random.Random(0))
    assert writer().split()
    asker = asker_from_config(Config(**{"trash_talk.provider": "template"}))
    assert asker.tokens_consumed == 0
    assert isinstance(resolve_trash_talk(Config(), random.Random(0)), TrashTalk)
    assert isinstance(resolve_trash_talk(Config(**{"trash_talk.provider": "unknown"}), random.Random(0)), TrashTalk)


def test_live_ollama_resolver_uses_grounded_hints_with_private_belief():
    writer = resolve_hint_writer(
        Config(**{"trash_talk.provider": "ollama"}), rng=random.Random(0)
    )
    assert isinstance(writer, LlmTrashTalk)
    assert writer.uses_llm

    class RuntimeConfig(Config):
        def get(self, key, default=None):
            return super().get(key, 5 if key == "trash_talk.timeout_seconds" else default)

    class GroundedWriter:
        last_source = "llm"
        last_fallback_reason = ""

        def say(self, state, belief, setting, opponent_hint, deadline):
            assert state.position == (3, 3)
            assert belief.most_likely() == (0, 0)
            return "Catch me north", "lie", "", ""

    runtime = SimpleNamespace(
        hint_writer=GroundedWriter(),
        state=OwnGameState((3, 3), 7),
        belief=BeliefGrid(7),
        config=RuntimeConfig(),
        _last_police_hint="",
    )
    hint, decision = _write_hint(runtime, Decision(MoveType.HOLD, None))
    assert hint == "Catch me north"
    assert decision.hint_source == "llm"


def test_alternate_provider_and_custom_brain_use_injected_gatekeeper(monkeypatch):
    calls = []

    class Gate:
        def execute(self, function, *args):
            calls.append(args)
            return function(*args)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"response": '{"action_id":"H0","message":"x",'
                               '"confidence":0.9,"reasoning":"r"}'}).encode()

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    provider = resolve_trash_talk(
        Config(**{"trash_talk.provider": "ollama", "play.hint_max_words": 15}),
        random.Random(0), gatekeeper=Gate()
    )
    assert provider.uses_llm
    state, belief = OwnGameState((3, 3), 7), BeliefGrid(7)
    provider.say(state, belief, "", "")
    assert calls
    move = MobilityThiefBrain().decide(state, belief).action()
    assert move is not None
