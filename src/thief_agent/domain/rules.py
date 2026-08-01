"""Terminal conditions evaluated by the Thief peer against its own state."""

from thief_agent.constants import Cell
from thief_agent.domain.own_state import OwnGameState

CAPTURE = "capture"
SURVIVAL = "survival"
TIMEOUT = "timeout"
TECHNICAL_LOSS = "technical_loss"


class GameRules:
    """Thief-side end-of-game conditions."""

    def __init__(self, max_steps: int, survival_threshold: int) -> None:
        self.max_steps = max_steps
        self.survival_threshold = survival_threshold

    def survival_result(self, state: OwnGameState) -> str | None:
        """Return survival once the Thief reaches its required threshold."""
        return SURVIVAL if state.step_number >= self.survival_threshold else None

    def out_of_steps(self, state: OwnGameState) -> bool:
        """Return whether the hard move ceiling has been reached."""
        return state.step_number >= self.max_steps

    @staticmethod
    def is_captured(state: OwnGameState, claim: Cell) -> bool:
        """Answer a Police capture claim honestly."""
        return state.position == tuple(claim)

    @staticmethod
    def barrier_captures(state: OwnGameState, barrier_cell: Cell) -> bool:
        """Return whether a newly declared Police barrier captures the Thief."""
        return state.position == tuple(barrier_cell)

    @staticmethod
    def confinement_capture(state: OwnGameState) -> bool:
        """Return whether Police barriers and board edges leave no escape."""
        return state.is_confined()
