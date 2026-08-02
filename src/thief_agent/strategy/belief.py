"""The Thief's belief about the unseen Police position."""

from thief_agent.constants import Cell


class BeliefGrid:
    """Small probability grid used by the Thief strategy.

    The Police position is never authoritative here. This grid only stores
    what the Thief currently believes from peer observations.
    """

    def __init__(self, board_size: int) -> None:
        if board_size < 1:
            raise ValueError("Belief grid size must be positive")
        self.size = board_size
        probability = 1.0 / (board_size * board_size)
        self._probabilities = [
            [probability for _ in range(board_size)] for _ in range(board_size)
        ]

    def _normalize(self) -> None:
        total = sum(sum(row) for row in self._probabilities)
        if total <= 0:
            probability = 1.0 / (self.size * self.size)
            self._probabilities = [
                [probability for _ in range(self.size)] for _ in range(self.size)
            ]
            return
        self._probabilities = [
            [value / total for value in row] for row in self._probabilities
        ]

    def observe(self, cell: Cell, weight: float = 1.0) -> None:
        """Increase the probability of an observed cell and renormalize."""
        row, column = cell
        if not (0 <= row < self.size and 0 <= column < self.size):
            raise ValueError(f"Observed cell {cell} is off the belief grid")
        self._probabilities[row][column] *= max(0.0, weight)
        self._normalize()

    def exclude(self, cell: Cell) -> None:
        """Rule out a cell after the Thief proves it is not occupied."""
        row, column = cell
        if not (0 <= row < self.size and 0 <= column < self.size):
            return
        self._probabilities[row][column] = 0.0
        self._normalize()

    def most_likely(self) -> Cell:
        """Return the cell with the greatest current probability."""
        return max(
            ((row, column) for row in range(self.size) for column in range(self.size)),
            key=lambda cell: self._probabilities[cell[0]][cell[1]],
        )

    def as_matrix(self) -> list[list[float]]:
        """Return a defensive copy for strategy and presentation layers."""
        return [row[:] for row in self._probabilities]
