"""Immutable Thief action vocabulary and legal movement directions.

These are physics, not configuration. The specification (Appendix Vav, table 15)
marks the move set as *fixed*: a single orthogonal step or staying put, with
diagonal movement forbidden. Modelling only N/S/E/W here means an illegal
diagonal cannot be represented at all, rather than merely being rejected later.
"""

from enum import StrEnum

# (row, column). The row index grows downward/south, matching the coordinate
# system agreed in config/*/game.json ("axis_origin_corner": "top-left").
Cell = tuple[int, int]


class MoveType(StrEnum):
    """The actions this Thief peer may take on its turn."""

    MOVE = "MOVE"  # step one cell orthogonally
    HOLD = "HOLD"  # stay put


class Direction(StrEnum):
    """The four orthogonal directions. Diagonals are illegal by specification."""

    N = "N"
    S = "S"
    E = "E"
    W = "W"


DELTAS: dict[Direction, tuple[int, int]] = {
    Direction.N: (-1, 0),
    Direction.S: (1, 0),
    Direction.E: (0, 1),
    Direction.W: (0, -1),
}

VERDICT_TRUTH = "truth"
VERDICT_LIE = "lie"

# Crypto: nonce length (bytes) for commit-reveal sealing.
NONCE_BYTES = 16

# Fixed game texts (protocol messages, not tunables).
FALLBACK_HINT = "I keep moving through the streets."  # generic but contains a location cue
FINAL_CAUGHT_HINT = "You got me."
NO_HINT_PLACEHOLDER = "(silence)"
