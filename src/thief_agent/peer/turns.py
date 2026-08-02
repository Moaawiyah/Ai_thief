"""Pure helpers for sealing Thief turns and constructing wire messages."""

from datetime import UTC, datetime

from thief_agent.domain.actions import Action
from thief_agent.domain.crypto import CommitReveal
from thief_agent.domain.protocol import TurnMessage


def state_descriptor(state) -> str:
    barriers = sorted([list(cell) for cell in state.barriers])
    return (
        f"grid={state.board.size}x{state.board.size};"
        f"self={list(state.position)};barriers={barriers}"
    )


def seal_step(state, action: Action, decision) -> dict:
    """Seal the Thief's already-applied state and action."""
    payload = {
        "step": state.step_number,
        "state": state_descriptor(state),
        "position": list(state.position),
        "move": str(action),
        "intent": decision.verdict,
        "verdict": decision.verdict,
        "hint": decision.hint,
    }
    return {"payload": payload, **CommitReveal.seal(payload)}


def turn_message(record: dict, hint: str, claim_response: dict | None, win: bool) -> dict:
    """Build the public Thief message for one sealed step."""
    message = TurnMessage(
        step=record["payload"]["step"],
        sender="thief",
        hint=hint,
        smell_grid={},
        commit=record["commit"],
        timestamp=datetime.now(UTC).isoformat(),
        claim_response=claim_response,
        win_claim={"type": "survival"} if win else None,
    )
    return message.to_dict()


def terminal_message(record: dict, step: int, claim_response: dict | None) -> dict:
    """Notify the opponent after a claim/barrier ends the game."""
    message = TurnMessage(
        step=step,
        sender="thief",
        hint="You caught me.",
        smell_grid={},
        commit=record["commit"],
        timestamp=datetime.now(UTC).isoformat(),
        claim_response=claim_response,
    )
    return message.to_dict()
