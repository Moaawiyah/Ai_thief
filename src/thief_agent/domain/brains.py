"""Pure-Python Thief decision policy adapted from the reference brain.

Override point for extension (see strategy/team_strategy.py): `_pick_move`.
`enable_tactics` lets an opt-in constrained-LLM chooser (strategy/llm_tactics.py)
override the move while this heuristic remains the deterministic fallback.
"""

import time
from dataclasses import dataclass

from thief_agent.constants import Cell, Direction, MoveType
from thief_agent.domain.actions import Action
from thief_agent.domain.belief import BeliefGrid
from thief_agent.domain.own_state import OwnGameState

__all__ = ["Decision", "BrainBase", "ThiefBrain"]


@dataclass(frozen=True)
class Decision:
    """One physical action, one verbal hint, and their audit evidence."""

    move_type: MoveType
    direction: Direction | None
    hint: str = "The trail goes cold."
    verdict: str = "lie"
    reasoning: str = ""
    fallback: bool = False
    random_move: bool = False
    response_seconds: float = 0.0
    prompt_text: str = ""
    strategy_source: str = "heuristic"
    strategy_action_id: str = ""
    strategy_prompt: str = ""
    strategy_reasoning: str = ""
    fallback_reason: str = ""
    hint_source: str = "template"
    hint_fallback_reason: str = ""

    def action(self) -> Action:
        """Convert the wire-facing decision to the domain value object."""
        return Action(self.move_type, self.direction)


class BrainBase:
    """Strategy seam: choose only from legal moves supplied by the domain."""

    def __init__(self) -> None:
        self._tactics = None

    def enable_tactics(self, tactics) -> None:
        """Attach an opt-in chooser while retaining this brain as fallback."""
        self._tactics = tactics

    def decide(
        self,
        state: OwnGameState,
        belief: BeliefGrid | None = None,
        opponent_hint: str = "",
        setting: str = "",
        barriers_max: int = 0,
        deadline_seconds: float | None = None,
        **_: object,
    ) -> Decision:
        del setting, barriers_max
        started = time.perf_counter()
        move_type, direction = self._decide_move(state, belief)
        source, action_id, prompt, reasoning, fallback_reason = "heuristic", "", "", "", ""
        used_fallback = False
        if self._tactics is not None:
            choice = self._tactics.choose(
                state, belief, move_type, direction, opponent_hint, deadline_seconds
            )
            move_type, direction = choice.move_type, choice.direction
            source, action_id = choice.source, choice.action_id
            prompt, reasoning = choice.prompt, choice.reasoning
            fallback_reason = choice.fallback_reason
            used_fallback = source != "llm"
        return Decision(
            move_type,
            direction,
            fallback=used_fallback,
            response_seconds=round(time.perf_counter() - started, 2),
            strategy_source=source,
            strategy_action_id=action_id,
            strategy_prompt=prompt,
            strategy_reasoning=reasoning,
            fallback_reason=fallback_reason,
        )

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
