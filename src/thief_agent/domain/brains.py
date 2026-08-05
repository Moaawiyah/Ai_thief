"""Pure-Python Thief decision policy adapted from the reference brain."""

from dataclasses import dataclass

from thief_agent.constants import Cell, Direction, MoveType
from thief_agent.domain.actions import Action
from thief_agent.domain.belief import BeliefGrid
from thief_agent.domain.own_state import OwnGameState


@dataclass(frozen=True)
class Decision:
    """A strategy decision; the move never depends on an LLM."""

    move_type: MoveType
    direction: Direction | None
    hint: str = "The trail goes cold."
    verdict: str = "lie"
    reasoning: str = ""

    def action(self) -> Action:
        """Convert the wire-facing decision to the domain value object."""
        return Action(self.move_type, self.direction)


class BrainBase:
    """Strategy seam: choose only from legal moves supplied by the domain."""

    def decide(
        self,
        state: OwnGameState,
        belief: BeliefGrid | None = None,
        opponent_hint: str = "",
        setting: str = "",
        barriers_max: int = 0,
        **_: object,
    ) -> Decision:
        del opponent_hint, setting, barriers_max
        move_type, direction = self._decide_move(state, belief)
        return Decision(move_type, direction)

    def _decide_move(
        self, state: OwnGameState, belief: BeliefGrid | None
    ) -> tuple[MoveType, Direction | None]:
        moves = state.board.legal_moves(state.position, state.barriers)
        if not moves:
            return MoveType.HOLD, None
        direction, _ = self._pick_move(moves, state, belief)
        return MoveType.MOVE, direction

    def _pick_move(
        self,
        moves: list[tuple[Direction, Cell]],
        state: OwnGameState,
        belief: BeliefGrid | None,
    ) -> tuple[Direction, Cell]:
        raise NotImplementedError


class ThiefBrain(BrainBase):
    """Evade the believed Police and prefer cells not visited before."""

    def _pick_move(self, moves, state, belief):
        threat = belief.most_likely() if belief is not None else (0, 0)
        return max(
            moves,
            key=lambda move: (
                state.board.distance(move[1], threat),
                move[1] not in state.visited,
            ),
        )
