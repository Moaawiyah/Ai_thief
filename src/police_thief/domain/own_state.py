"""OwnGameState: the only state a peer is authoritative for -- its own.

There is no shared board and no referee. A peer knows its true position, the
cells it has visited, and the barriers that have been *publicly declared* (its
own plus the opponent's, which are impassable for both sides). It deliberately
never stores the opponent's position: that is only ever a belief, reconstructed
later from scent observations.
"""

from police_thief.constants import Cell, Direction, MoveType, Role
from police_thief.domain.actions import Action
from police_thief.domain.board import Board


class OwnGameState:
    """One peer's private game state and its per-step move log."""

    def __init__(self, role: Role, start: Cell, board_size: int) -> None:
        self.board = Board(board_size)
        if not self.board.in_bounds(start):
            raise ValueError(f"Start cell {start} is off a {board_size}x{board_size} board")
        self.role = role
        self.position: Cell = start
        self.visited: set[Cell] = {start}
        self.barriers: set[Cell] = set()  # every known barrier: mine and declared
        self.my_barriers = 0
        self.step_number = 0
        self.log: list[dict] = []

    @property
    def unique_cells(self) -> int:
        """Distinct cells occupied so far. Holding still never adds to this."""
        return len(self.visited)

    def note_barrier(self, cell: Cell) -> None:
        """Record a barrier the opponent declared. Barriers are irreversible."""
        self.barriers.add(cell)

    def is_confined(self) -> bool:
        """True when no legal step remains from here (Appendix He, rule 47)."""
        return not self.board.legal_moves(self.position, self.barriers)

    def apply_move(self, action: Action, barriers_max: int = 0) -> bool:
        """Apply my own action. Returns False and leaves state untouched if illegal."""
        placed: Cell | None = None
        if action.move_type is MoveType.BARRIER:
            placed = self._place_barrier(action.direction, barriers_max)
            if placed is None:
                return False
        elif action.move_type is MoveType.MOVE:
            target = self.board.step(self.position, action.direction, self.barriers)
            if target is None:
                return False
            self.position = target
            self.visited.add(target)
        # HOLD falls through: the step still counts, but nothing about me changes.
        self._record(action, placed)
        return True

    def last_barrier(self) -> Cell | None:
        """The cell walled by my last logged action, if it was a barrier placement."""
        if self.log and self.log[-1]["barrier"]:
            row, col = self.log[-1]["barrier"]
            return (row, col)
        return None

    def _place_barrier(self, direction: Direction | None, barriers_max: int) -> Cell | None:
        """Wall a cell within one step. A missing direction means the cell underfoot.

        Only the police may build, and only within the agreed quota -- every
        placement is a resource decision, so an exhausted quota is a plain
        rejection rather than a silent no-op.
        """
        if self.role is not Role.POLICE or self.my_barriers >= barriers_max:
            return None
        if direction is None:
            target: Cell | None = self.position
        else:
            target = self.board.step(self.position, direction, self.barriers)
        if target is None or target in self.barriers:
            return None
        self.barriers.add(target)
        self.my_barriers += 1
        return target

    def _record(self, action: Action, placed: Cell | None) -> None:
        self.step_number += 1
        self.log.append(
            {
                "step": self.step_number,
                "position": [self.position[0], self.position[1]],
                "move": str(action),
                "unique_cells": self.unique_cells,
                "barrier": [placed[0], placed[1]] if placed else None,
            }
        )
