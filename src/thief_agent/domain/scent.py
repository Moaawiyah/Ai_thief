"""The pheromone field emitted by the Thief and received from the Police.

Each peer maintains its own field.  A turn first fades the existing trail and
then deposits a fresh radial emission, so the current cell is always at the
agreed centre intensity.  Wire values use ``"row,column"`` keys and are
rounded to three decimals for deterministic cross-peer behavior.
"""

from thief_agent.constants import Cell
from thief_agent.domain.scent_kernel import emission_kernel

_TRACE_FLOOR = 0.01


class ScentField:
    """Cell intensities laid down and faded over the course of a game."""

    def __init__(
        self,
        board_size: int,
        grid_size: int,
        decay: float,
        emit_intensity: float,
        min_center: float,
    ) -> None:
        if board_size < 1:
            raise ValueError(f"Board size must be positive, got {board_size}")
        if grid_size < 1 or grid_size % 2 == 0:
            raise ValueError(f"Scent field size must be positive and odd, got {grid_size}")
        self._board_size = board_size
        self._grid_size = grid_size
        self._decay = decay
        self._emit_intensity = emit_intensity
        self._min_center = min_center
        self._values: dict[Cell, float] = {}

    @classmethod
    def from_terms(cls, terms: dict) -> "ScentField":
        """Build physical scent parameters from the signed agreement."""
        return cls(
            terms["board_size"],
            terms["smell_grid_size"],
            terms["decay_per_step"],
            terms["emit_intensity"],
            terms["min_center_intensity"],
        )

    def emit(self, position: Cell) -> dict[str, float]:
        """Decay the old trail, deposit at ``position``, and return its wire form."""
        self.decay_all()
        self.deposit(position)
        return self.snapshot()

    def deposit(self, center: Cell, intensity: float | None = None) -> None:
        """Lay a radial emission, retaining the strongest value per cell."""
        if intensity is None:
            intensity = self._emit_intensity
        if intensity < self._min_center:
            raise ValueError(
                f"Centre intensity {intensity} is below the agreed minimum {self._min_center}"
            )
        for cell, value in self._radial(center, intensity).items():
            self._values[cell] = max(self._values.get(cell, 0.0), value)

    def absorb(self, cells: dict | None) -> None:
        """Merge a received grid; malformed foreign entries are ignored."""
        for key, value in (cells or {}).items():
            cell = self._parse(key)
            if cell is not None and isinstance(value, int | float):
                self._values[cell] = max(self._values.get(cell, 0.0), float(value))

    def decay_all(self) -> None:
        """Multiply every trace by ``1 - decay`` and remove imperceptible dust."""
        for cell in list(self._values):
            faded = round(self._values[cell] * (1.0 - self._decay), 3)
            if faded >= _TRACE_FLOOR:
                self._values[cell] = faded
            else:
                del self._values[cell]

    def intensity_at(self, cell: Cell) -> float:
        return self._values.get(cell, 0.0)

    def snapshot(self) -> dict[str, float]:
        """Return ``{"row,column": intensity}`` for all live traces."""
        return {
            f"{row},{column}": value for (row, column), value in self._values.items() if value > 0.0
        }

    def _radial(self, center: Cell, intensity: float) -> dict[Cell, float]:
        emitted: dict[Cell, float] = {}
        for (d_row, d_column), value in emission_kernel(self._grid_size, intensity).items():
            cell = (center[0] + d_row, center[1] + d_column)
            if self._in_bounds(cell):
                emitted[cell] = value
        return emitted

    def _in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self._board_size and 0 <= cell[1] < self._board_size

    def _parse(self, key: str) -> Cell | None:
        try:
            row_text, column_text = str(key).split(",")
            cell = (int(row_text), int(column_text))
        except ValueError:
            return None
        return cell if self._in_bounds(cell) else None
