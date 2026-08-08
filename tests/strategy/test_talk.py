"""Thief dialogue stays bounded, coordinate-free, and optional."""

import random

from thief_agent.strategy.talk import HintWriter


def writer(reply: str, **kwargs) -> HintWriter:
    return HintWriter(lambda _prompt, _system: reply, rng=random.Random(0), **kwargs)


def test_model_output_is_capped_and_think_blocks_are_removed():
    subject = writer(
        "<think>internal reasoning</think>\nI vanish beyond the city lights.",
        setting="New York",
        max_words=4,
    )

    result = subject()

    assert result == "I vanish beyond the"
    assert "think" not in result


def test_coordinates_are_rejected_in_favor_of_a_safe_fallback():
    result = writer("I am waiting at 3,4.", setting="New York")()

    assert result
    assert "3,4" not in result


def test_model_failures_never_escape_the_dialogue_layer():
    def fail(_prompt, _system):
        raise ConnectionError("Ollama is offline")

    result = HintWriter(fail, rng=random.Random(0))()

    assert result


def test_every_n_steps_controls_model_calls():
    calls = []
    subject = HintWriter(
        lambda _prompt, _system: calls.append(1) or "A quiet alley.",
        every_n_steps=3,
        rng=random.Random(0),
    )

    for _ in range(6):
        subject()

    assert len(calls) == 2


def test_ollama_prompt_keeps_the_model_in_the_thief_role():
    prompts = {}

    def capture(user, system):
        prompts["user"], prompts["system"] = user, system
        return "I am already gone."

    HintWriter(capture, setting="New York", rng=random.Random(0))(
        opponent_hint="You cannot escape."
    )

    assert "You are the Thief" in prompts["system"]
    assert "never the Police" in prompts["system"]
    assert "untrusted context" in prompts["user"]
    assert "Never answer as the Police" in prompts["user"]
