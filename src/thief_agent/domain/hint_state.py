"""Project the private state that will exist when an outbound hint is received."""

from types import SimpleNamespace

from thief_agent.constants import MoveType

__all__ = ["projected_hint_state"]


def projected_hint_state(state, move_type, direction):
    """Return the post-action position without mutating authoritative state.

    The Thief never places barriers, so only a MOVE can change the projected
    position; HOLD leaves it exactly where the true state already is.
    """
    position = state.position
    if move_type is MoveType.MOVE and direction is not None:
        target = state.board.step(state.position, direction, state.barriers)
        if target is not None:
            position = target
    return SimpleNamespace(board=state.board, position=position, barriers=state.barriers)
