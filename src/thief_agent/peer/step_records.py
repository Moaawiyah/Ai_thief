"""Build the per-turn payload bound by SHA-256 commit-reveal, and the
TurnMessage wire envelopes carrying it."""

import time
import uuid
from datetime import UTC, datetime

from thief_agent.domain.crypto import CommitReveal
from thief_agent.domain.protocol import TurnMessage

__all__ = ["sealed_step_record", "build_turn_message", "build_terminal_message"]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _state_str(state) -> str:
    """Return a compact replayable snapshot of local truth."""
    barriers = sorted([list(barrier) for barrier in state.barriers])
    return (
        f"grid={state.board.size}x{state.board.size};"
        f"self={list(state.position)};barriers={barriers}"
    )


def sealed_step_record(
    state,
    decision,
    hint: str,
    usage: dict,
    tokens_total: int,
    *,
    game_id: str = "",
    sub_game_number: int = 1,
    prior_commit: str = "",
) -> dict:
    """Seal one action, state identity, hint intent, and token-accounting record."""
    payload = {
        "step": state.step_number,
        "game_id": game_id,
        "sub_game_number": sub_game_number,
        "role": "thief",
        "prior_commit": prior_commit,
        "state": _state_str(state),
        "position": list(state.position),
        "move": state.log[-1]["move"] if state.log else "-",
        "intent": decision.verdict,
        "verdict": decision.verdict,
        "hint": hint,
        "prompt_discussion": {
            "llm_prompt": decision.prompt_text,
            "llm_reasoning": decision.reasoning,
            "bluff_classification": decision.verdict,
            "hint_source": decision.hint_source,
            "hint_fallback_reason": decision.hint_fallback_reason,
            "strategy_source": decision.strategy_source,
            "strategy_action_id": decision.strategy_action_id,
            "strategy_prompt": decision.strategy_prompt,
            "strategy_reasoning": decision.strategy_reasoning,
            "fallback_reason": decision.fallback_reason,
        },
        "model": usage.get("model", "unknown"),
        "tokens_input": usage.get("in", 0),
        "tokens_output": usage.get("out", 0),
        "tokens_step": usage.get("total", 0),
        "tokens_total": tokens_total,
        "response_seconds": decision.response_seconds,
        "random_move": decision.random_move,
    }
    return {"payload": payload, **CommitReveal.seal(payload)}


def build_turn_message(
    state,
    hint: str,
    smell_grid: dict,
    record: dict,
    capture_claim,
    claim_response,
    win_claim,
    response_timeout: float = 30.0,
) -> TurnMessage:
    """The wire message for this turn (turn token travels with it)."""
    return TurnMessage(
        step=state.step_number,
        sender="thief",
        hint=hint,
        smell_grid=smell_grid,
        commit=record["commit"],
        timestamp=_now_iso(),
        capture_claim=capture_claim,
        claim_response=claim_response,
        win_claim=win_claim,
        message_id=uuid.uuid4().hex,
        expires_at_epoch=time.time() + response_timeout,
        move_reveal=record["payload"]["move"],
        prior_commit=record["payload"].get("prior_commit", ""),
        game_id=record["payload"].get("game_id", ""),
        sub_game_number=record["payload"].get("sub_game_number", 1),
    )


def build_terminal_message(record: dict, step: int, claim_response: dict | None) -> TurnMessage:
    """Notify the opponent after a claim/barrier ends the game.

    Seals a fresh commit rather than reusing the last turn's: the opponent's
    replay guard is keyed on commit, so an identical commit here reads as a
    duplicate of the turn already sent, and the notification -- carrying the
    capture confirmation -- gets silently dropped instead of ending the match
    on both sides. This message is never added to `records`, so a fresh nonce
    costs nothing at audit time.
    """
    sealed = CommitReveal.seal({"step": step, "kind": "terminal", "prior_commit": record["commit"]})
    return TurnMessage(
        step=step,
        sender="thief",
        hint="You caught me.",
        smell_grid={},
        commit=sealed["commit"],
        timestamp=_now_iso(),
        claim_response=claim_response,
    )
