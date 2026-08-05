"""Bayesian belief fusion for the unseen Police position.

The Thief never receives the Police's true position during play.  It instead
runs the same predict/update filter as the reference peer:

1. ``diffuse`` spreads belief over legal Police moves;
2. ``scale`` can fold non-scent evidence into the prior;
3. ``observe_smell`` applies the received pheromone field as a likelihood.

The order is important.  Scent is evidence about the Police's new position,
so it must sharpen the prediction after movement rather than being blurred by
the next prediction step.
"""

from thief_agent.constants import Cell

DEFAULT_SMELL_TRUST = 4.0
_EPSILON = 1e-9


class BeliefGrid:
    """A normalized probability distribution over the Police's cell."""

    _OFFSETS = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))

    def __init__(self, board_size: int, smell_trust: float = DEFAULT_SMELL_TRUST) -> None:
        if board_size < 1:
            raise ValueError("Belief grid size must be positive")
        self.size = board_size
        self._smell_trust = smell_trust
        probability = 1.0 / (board_size * board_size)
        self._probabilities = [[probability for _ in range(board_size)] for _ in range(board_size)]

    @classmethod
    def from_config(cls, terms: dict, config) -> "BeliefGrid":
        """Use signed board terms and this peer's private trust tuning."""
        trust = config.get("belief.smell_trust", DEFAULT_SMELL_TRUST)
        return cls(terms["board_size"], trust)

    def observe_smell(self, cells: dict | None) -> None:
        """Multiply scented cells by ``1 + trust * intensity`` and normalize."""
        for key, value in (cells or {}).items():
            cell = self._parse(key)
            if cell is not None and isinstance(value, int | float):
                row, column = cell
                self._probabilities[row][column] *= 1.0 + self._smell_trust * float(value)
        self._normalize()

    def diffuse(self) -> None:
        """Predict one Police turn using stay-put and orthogonal movement."""
        fresh = [[0.0] * self.size for _ in range(self.size)]
        for row in range(self.size):
            for column in range(self.size):
                mass = self._probabilities[row][column]
                if mass < _EPSILON:
                    continue
                targets = [
                    (row + d_row, column + d_column)
                    for d_row, d_column in self._OFFSETS
                    if self._in_bounds((row + d_row, column + d_column))
                ]
                share = mass / len(targets)
                for target_row, target_column in targets:
                    fresh[target_row][target_column] += share
        self._probabilities = fresh
        self._normalize()

    def observe_likelihoods(self, evidence: dict[Cell, float]) -> None:
        """Apply soft evidence from a parsed verbal hint and renormalize."""
        for (row, column), likelihood in evidence.items():
            if self._in_bounds((row, column)):
                self._probabilities[row][column] *= max(_EPSILON, float(likelihood))
        self._normalize()

    def scale(self, cells, factor: float) -> None:
        """Reweight selected cells for evidence that is not scent."""
        for cell in cells:
            if self._in_bounds(cell):
                self._probabilities[cell[0]][cell[1]] *= factor
        self._normalize()

    def observe(self, cell: Cell, weight: float = 1.0) -> None:
        """Compatibility helper for direct local observations and old callers."""
        if not self._in_bounds(cell):
            raise ValueError(f"Observed cell {cell} is off the belief grid")
        self._probabilities[cell[0]][cell[1]] *= max(0.0, weight)
        self._normalize()

    def exclude(self, cell: Cell) -> None:
        """Rule out a cell after a barrier or other observation excludes it."""
        if self._in_bounds(cell):
            self._probabilities[cell[0]][cell[1]] = 0.0
            self._normalize()

    def most_likely(self) -> Cell:
        """Return the row-major deterministic argmax."""
        best, best_probability = (0, 0), -1.0
        for row in range(self.size):
            for column in range(self.size):
                probability = self._probabilities[row][column]
                if probability > best_probability:
                    best, best_probability = (row, column), probability
        return best

    def as_matrix(self) -> list[list[float]]:
        """Return a defensive copy for strategy, logging, and presentation."""
        return [row[:] for row in self._probabilities]

    def _normalize(self) -> None:
        total = sum(sum(row) for row in self._probabilities)
        if total < _EPSILON:
            probability = 1.0 / (self.size * self.size)
            self._probabilities = [
                [probability for _ in range(self.size)] for _ in range(self.size)
            ]
            return
        self._probabilities = [[value / total for value in row] for row in self._probabilities]

    def _in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.size and 0 <= cell[1] < self.size

    def _parse(self, key: str) -> Cell | None:
        try:
            row_text, column_text = str(key).split(",")
            cell = (int(row_text), int(column_text))
        except ValueError:
            return None
        return cell if self._in_bounds(cell) else None
