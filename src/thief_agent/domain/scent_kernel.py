"""The fixed shape of one pheromone emission.

The 5x5 radial window is shared with the Police peer.  Keeping the kernel
separate from the field makes the wire-facing decay and merge rules easier to
test and prevents strategy code from changing the physical scent model.
"""

import math

_FALLOFF_SIGMA = 1.15


def emission_kernel(grid_size: int, intensity: float) -> dict[tuple[int, int], float]:
    """Return one emission as relative cell offsets and rounded intensities."""
    half = grid_size // 2
    spread = 2.0 * _FALLOFF_SIGMA**2
    return {
        (row, column): round(
            intensity * math.exp(-(row**2 + column**2) / spread), 3
        )
        for row in range(-half, half + 1)
        for column in range(-half, half + 1)
    }
