"""Terminal conditions, evaluated by each peer against its OWN state.

No referee exists, so nothing here adjudicates the opponent. A peer answers
capture claims about itself truthfully and claims its own survival; both are
sealed into the commit-reveal log and proven at the end-of-game audit, which is
what makes lying pointless rather than merely discouraged.
"""

from police_thief.constants import Cell, Role
from police_thief.domain.own_state import OwnGameState

# Outcome strings shared with the scoring table and the result JSON.
CAPTURE = "capture"
SURVIVAL = "survival"
TIMEOUT = "timeout"
TECHNICAL_LOSS = "technical_loss"


class GameRules:
    """The agreed end-of-game conditions for one sub-game.

    `max_steps` is the hard move ceiling for the sub-game; `survival_threshold`
    is how long the thief must last to win. The specification keeps them as two
    separate parameters even though both default to the same value.
    """

    def __init__(self, max_steps: int, survival_threshold: int) -> None:
        self.max_steps = max_steps
        self.survival_threshold = survival_threshold

    def thief_result(self, state: OwnGameState) -> str | None:
        """The thief's own win claim: SURVIVAL once it has outlasted the threshold."""
        if state.role is not Role.THIEF:
            return None
        return SURVIVAL if state.step_number >= self.survival_threshold else None

    def out_of_steps(self, state: OwnGameState) -> bool:
        """True once the sub-game's hard move ceiling has been reached."""
        return state.step_number >= self.max_steps

    @staticmethod
    def is_captured(state: OwnGameState, claim: Cell) -> bool:
        """Honest answer to a capture claim: am I really standing on that cell?"""
        return state.position == tuple(claim)

    @staticmethod
    def barrier_captures(state: OwnGameState, barrier_cell: Cell) -> bool:
        """A barrier dropped on the thief's own cell is a capture (Appendix He, 46)."""
        return state.role is Role.THIEF and state.position == tuple(barrier_cell)

    @staticmethod
    def confinement_capture(state: OwnGameState) -> bool:
        """A thief left with no legal step is captured too (Appendix He, 47)."""
        return state.role is Role.THIEF and state.is_confined()
