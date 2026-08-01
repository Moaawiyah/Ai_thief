"""Authoritative state owned by the Thief peer.

The Thief owns its true position and movement history. It records barriers
declared by the Police as external observations, but it never places barriers
or stores Police-owned resources.
"""

from thief_agent.constants import Cell, MoveType
from thief_agent.domain.actions import Action
from thief_agent.domain.board import Board


class OwnGameState:
    """Private Thief state and its per-turn move log."""

    def __init__(self, start: Cell, board_size: int) -> None:
        self.board = Board(board_size)
        if not self.board.in_bounds(start):
            raise ValueError(f"Start cell {start} is off a {board_size}x{board_size} board")
        self.position: Cell = start
        self.visited: set[Cell] = {start}
        self.barriers: set[Cell] = set()
        self.step_number = 0
        self.log: list[dict] = []

    @property
    def unique_cells(self) -> int:
        """Distinct cells occupied so far. Holding still never adds to this."""
        return len(self.visited)

    def note_barrier(self, cell: Cell) -> None:
        """Record a barrier declared by the Police. Barriers are irreversible."""
        self.barriers.add(cell)

    def is_confined(self) -> bool:
        """True when no legal step remains from the Thief's position."""
        return not self.board.legal_moves(self.position, self.barriers)

    def apply_move(self, action: Action) -> bool:
        """Apply a Thief move or hold, leaving state untouched if illegal."""
        if action.move_type is MoveType.MOVE:
            target = self.board.step(self.position, action.direction, self.barriers)
            if target is None:
                return False
            self.position = target
            self.visited.add(target)
        elif action.move_type is not MoveType.HOLD:
            return False
        self._record(action)
        return True

    def _record(self, action: Action) -> None:
        self.step_number += 1
        self.log.append(
            {
                "step": self.step_number,
                "position": [self.position[0], self.position[1]],
                "move": str(action),
                "unique_cells": self.unique_cells,
            }
        )
