"""Free template hints; constrained/grounded LLM hints live in ``llm_hints.py``.

This is an alternate, richer hint-writer shape (mirrors the Police peer's
``TrashTalk``/``LlmTrashTalk`` hierarchy) available via
``talk_providers.resolve_trash_talk``. It coexists with — and does not
replace — Thief's simpler default ``strategy/talk.py:HintWriter``.
"""

import random

from thief_agent.constants import VERDICT_LIE, VERDICT_TRUTH

LANDMARKS: dict[str, list[str]] = {
    "New York": [
        "Times Square",
        "Central Park",
        "the Brooklyn Bridge",
        "Wall Street",
        "Harlem",
        "the East Village",
    ],
    "London": ["Big Ben", "Tower Bridge", "Camden", "Soho", "the Thames"],
    "Paris": ["the Eiffel Tower", "Montmartre", "the Louvre", "the Left Bank"],
}
_DEFAULT_LANDMARKS = ["downtown", "the old market", "the harbor", "the north gate"]
_THIEF_LINES = [
    "Catch me if you can - I'm slipping past {landmark}!",
    "Still one step ahead, near {landmark}.",
    "You'll never pin me down around {landmark}.",
    "Too slow, officer - {landmark} is mine.",
]

__all__ = ["TrashTalk"]


class TrashTalk:
    """Zero-token template provider and safe fallback base."""

    every_n_steps = 1
    uses_llm = False

    def __init__(self, rng: random.Random | None = None, max_words: int = 15):
        self._rng = rng or random.Random()
        self._turn = 0
        self.max_words = max(1, int(max_words))
        self.last_source = "template"
        self.last_fallback_reason = ""

    def _cap(self, hint: str) -> str:
        words = hint.split()
        return hint if len(words) <= self.max_words else " ".join(words[: self.max_words])

    def say(self, state, belief, setting, opponent_hint, deadline=None):
        del state, belief, opponent_hint, deadline
        self.last_source, self.last_fallback_reason = "template", ""
        hint, verdict = self._template(setting)
        return self._cap(hint), verdict, "", ""

    def _template(self, setting: str) -> tuple[str, str]:
        landmark = self._rng.choice(LANDMARKS.get(setting, _DEFAULT_LANDMARKS))
        hint = self._rng.choice(_THIEF_LINES).format(landmark=landmark)
        lying = self._rng.random() < 0.4
        return hint, (VERDICT_LIE if lying else VERDICT_TRUTH)
