"""Bayesian belief fusion for the unseen Police position.

The Thief never receives the Police's true position: ``diffuse`` predicts
(spreads belief over legal Police moves), ``observe_smell`` updates (the
pheromone field sharpens it as a likelihood), and ``scale`` folds in non-scent
evidence. Order matters -- scent must sharpen the prediction after movement,
not be blurred away by the next predict step.
"""

from thief_agent.constants import Cell
from thief_agent.domain.grid_utils import in_bounds, parse_cell

DEFAULT_SMELL_TRUST = 4.0
# Convexity of intensity->likelihood -- above 1, a cell faint relative to THIS reading's own
# peak is starved harder than the peak itself, regardless of the packet's absolute scale.
DEFAULT_SMELL_POWER = 3.0
# Sliver of the posterior re-mixed to uniform each turn -- readings are a trail, not independent.
DEFAULT_LEAK = 0.03
_EPSILON = 1e-9


class BeliefGrid:
    """A normalized probability distribution over the Police's cell."""

    _OFFSETS = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))

    def __init__(
        self,
        board_size: int,
        smell_trust: float = DEFAULT_SMELL_TRUST,
        smell_power: float = DEFAULT_SMELL_POWER,
        leak: float = DEFAULT_LEAK,
    ) -> None:
        if board_size < 1:
            raise ValueError("Belief grid size must be positive")
        self.size = board_size
        self._smell_trust = smell_trust
        self._smell_power = smell_power
        self._leak = leak
        probability = 1.0 / (board_size * board_size)
        self._probabilities = [[probability for _ in range(board_size)] for _ in range(board_size)]

    @classmethod
    def from_config(cls, terms: dict, config) -> "BeliefGrid":
        """Signed board terms and this peer's private trust/power/leak tuning."""
        trust = config.get("belief.smell_trust", DEFAULT_SMELL_TRUST)
        power = config.get("belief.smell_power", DEFAULT_SMELL_POWER)
        leak = config.get("belief.leak", DEFAULT_LEAK)
        return cls(terms["board_size"], trust, power, leak)

    def observe_smell(self, cells: dict | None) -> None:
        """``1 + trust * reading**power`` per scented cell, where ``reading`` is
        that cell's intensity relative to THIS reading's own peak, not an
        absolute value -- a field that has broadly faded still has a relatively
        freshest cell, and that is the one evidence should concentrate on.
        Normalize, then leak. Malformed entries are skipped, not fatal."""
        parsed: dict[Cell, float] = {}
        for key, value in (cells or {}).items():
            cell = parse_cell(key, self.size)
            if cell is not None and isinstance(value, int | float):
                parsed[cell] = min(1.0, max(0.0, float(value)))  # negative here can turn complex
        peak = max(parsed.values(), default=0.0)
        if peak > 0.0:
            for (row, column), intensity in parsed.items():
                reading = intensity / peak
                boost = 1.0 + self._smell_trust * reading**self._smell_power
                self._probabilities[row][column] *= boost
        self._normalize()
        self._leak_toward_uniform()

    def diffuse(self, barriers: set[Cell] | None = None) -> None:
        """Predict one Police turn using stay-put and orthogonal movement.

        A declared barrier is impassable, so a target cell in `barriers` is
        never a legal Police step and must not receive spread mass -- left
        unfiltered, probability keeps leaking onto cells Police can never
        reach, and the posterior never concentrates the way it should.
        """
        blocked = barriers or set()
        fresh = [[0.0] * self.size for _ in range(self.size)]
        for row in range(self.size):
            for column in range(self.size):
                mass = self._probabilities[row][column]
                if mass < _EPSILON:
                    continue
                targets = [
                    (row + d_row, column + d_column)
                    for d_row, d_column in self._OFFSETS
                    if in_bounds((row + d_row, column + d_column), self.size)
                    and (row + d_row, column + d_column) not in blocked
                ]
                if not targets:
                    targets = [(row, column)]  # walled in on every side: mass stays put
                share = mass / len(targets)
                for target_row, target_column in targets:
                    fresh[target_row][target_column] += share
        self._probabilities = fresh
        self._normalize()

    def observe_likelihoods(self, evidence: dict[Cell, float]) -> None:
        """Apply soft evidence from a parsed verbal hint and renormalize."""
        for (row, column), likelihood in evidence.items():
            if in_bounds((row, column), self.size):
                self._probabilities[row][column] *= max(_EPSILON, float(likelihood))
        self._normalize()

    def scale(self, cells, factor: float) -> None:
        """Reweight selected cells for evidence that is not scent."""
        for cell in cells:
            if in_bounds(cell, self.size):
                self._probabilities[cell[0]][cell[1]] *= factor
        self._normalize()

    def observe(self, cell: Cell, weight: float = 1.0) -> None:
        """Compatibility helper for direct local observations and old callers."""
        if not in_bounds(cell, self.size):
            raise ValueError(f"Observed cell {cell} is off the belief grid")
        self._probabilities[cell[0]][cell[1]] *= max(0.0, weight)
        self._normalize()

    def exclude(self, cell: Cell) -> None:
        """Rule out a cell after a barrier or other observation excludes it."""
        if in_bounds(cell, self.size):
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

    def _leak_toward_uniform(self) -> None:
        """Only ``observe_smell`` calls this -- others already normalize once a turn."""
        if self._leak <= 0.0:
            return
        probability = 1.0 / (self.size * self.size)
        self._probabilities = [
            [(1.0 - self._leak) * value + self._leak * probability for value in row]
            for row in self._probabilities
        ]
