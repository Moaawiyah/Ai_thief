"""Strict, grounded LLM hint generation with deterministic fallback."""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from thief_agent.strategy.hint_candidates import ranked_hint_candidates
from thief_agent.strategy.hint_prompt import build_hint_prompt
from thief_agent.strategy.trash_talk import TrashTalk

logger = logging.getLogger(__name__)

HINT_SCHEMA = {
    "type": "object",
    "properties": {
        "action_id": {"type": "string", "pattern": "^H[0-4]$"},
        "message": {"type": "string", "maxLength": 140},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string", "maxLength": 300},
    },
    "required": ["action_id", "message", "confidence", "reasoning"],
    "additionalProperties": False,
}
_FORBIDDEN = (
    "ignore previous",
    "system prompt",
    "developer message",
    "action_id",
    "follow these instructions",
)

__all__ = ["HINT_SCHEMA", "LlmTrashTalk"]


class LlmTrashTalk(TrashTalk):
    """Let an LLM choose and phrase one locally validated strategic claim.

    `ask` must accept ``(prompt, deadline, system)`` — distinct from
    ``strategy/talk.py``'s simpler ``ask(prompt, system)`` dialogue interface.
    """

    uses_llm = True

    def __init__(self, ask, rng=None, every_n_steps=1, model="", max_words=15, min_confidence=0.55):
        super().__init__(rng, max_words)
        self._ask = ask
        self.every_n_steps = max(1, int(every_n_steps or 1))
        self._model = model
        self._min_confidence = max(0.0, min(1.0, float(min_confidence)))

    def say(self, state, belief, setting, opponent_hint, deadline=None):
        self._turn += 1
        if self._turn % self.every_n_steps != 0 or state is None or belief is None:
            self.last_source = "template"
            return super().say(state, belief, setting, opponent_hint, deadline)
        candidates = ranked_hint_candidates(state, belief, setting)
        system, user = build_hint_prompt(state, belief, candidates, self.max_words)
        logged = f"[system]\n{system}\n\n[user]\n{user}"
        started = time.monotonic()
        try:
            raw = self._ask_bounded(user, deadline, system)
            source = "llm"
            try:
                candidate, message, reasoning = self._validate(raw, candidates)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                remaining = self._remaining(deadline, started)
                repair = (
                    f"{user}\n\nCORRECTION: the previous reply failed validation. "
                    "Choose again and copy the selected claim's safe_example EXACTLY "
                    "as message. Return only the required JSON."
                )
                raw = self._ask_bounded(repair, remaining, system)
                candidate, message, reasoning = self._validate(raw, candidates)
                logged += f"\n\n[repair_user]\n{repair}"
                source = "llm_retry"
            self.last_source, self.last_fallback_reason = source, ""
            return message, candidate.verdict, reasoning, logged
        except FutureTimeout:
            reason = "deadline"
        except json.JSONDecodeError:
            reason = "invalid_json"
        except (KeyError, TypeError, ValueError):
            reason = "invalid_schema"
        except Exception as exc:
            logger.warning("hint LLM failed: %s", exc)
            reason = "provider_error"
        best = candidates[0]
        self.last_source, self.last_fallback_reason = "grounded_fallback", reason
        return self._cap(best.fallback_message), best.verdict, "", logged

    @staticmethod
    def _remaining(deadline, started: float):
        if deadline is None:
            return None
        remaining = float(deadline) - (time.monotonic() - started)
        if remaining < 0.05:
            raise FutureTimeout()
        return remaining

    def _ask_bounded(self, prompt: str, deadline, system: str):
        if not deadline:
            return self._ask(prompt, deadline, system)
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self._ask, prompt, deadline, system)
            return future.result(timeout=deadline)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _validate(self, raw: str, candidates):
        data = json.loads(raw.strip())
        required = {"action_id", "message", "confidence", "reasoning"}
        if not isinstance(data, dict) or set(data) != required:
            raise TypeError("reply must contain exactly the hint schema")
        candidate = {item.action_id: item for item in candidates}.get(data["action_id"])
        confidence = float(data["confidence"])
        if candidate is None or not 0 <= confidence <= 1:
            raise ValueError("unknown hint or invalid confidence")
        if confidence < self._min_confidence:
            raise ValueError("unknown hint or low confidence")
        message = " ".join(str(data["message"]).split())
        lowered = message.casefold()
        if not message or len(message.split()) > self.max_words:
            raise ValueError("message violates word limit")
        zones = {item.zone for item in candidates if item.zone in lowered}
        other_cues = {
            item.cue.casefold()
            for item in candidates
            if item.action_id != candidate.action_id and item.cue.casefold() in lowered
        }
        if candidate.cue.casefold() not in lowered or zones != {candidate.zone}:
            raise ValueError("message is not grounded in selected claim")
        if other_cues:
            raise ValueError("message mixes multiple approved claims")
        if any(term in lowered for term in _FORBIDDEN) or any(c in message for c in "{}[]"):
            raise ValueError("message contains instruction-like content")
        return candidate, message, str(data["reasoning"])[:300]
