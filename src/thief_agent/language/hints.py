"""Parse coarse location language into likelihood evidence without using an LLM."""

from thief_agent.constants import Cell

_NORTH = ("north", "harlem", "central park", "uptown", "north gate")
_SOUTH = ("south", "wall street", "harbor", "downtown")
_EAST = ("east", "east village", "brooklyn bridge")
_WEST = ("west", "west side")
_CENTER = ("center", "central", "times square", "old market")

__all__ = ["infer_likelihoods"]


def _zone(text: str) -> str | None:
    """Return the strongest coarse zone named in a hint."""
    lowered = text.casefold()
    for zone, words in (
        ("north", _NORTH),
        ("south", _SOUTH),
        ("east", _EAST),
        ("west", _WEST),
        ("center", _CENTER),
    ):
        if any(word in lowered for word in words):
            return zone
    return None


def infer_likelihoods(hint: str, board_size: int) -> dict[Cell, float]:
    """Map a free-language location cue to soft per-cell likelihood multipliers."""
    zone = _zone(hint)
    if zone is None:
        return {}
    midpoint = (board_size - 1) / 2
    evidence: dict[Cell, float] = {}
    for row in range(board_size):
        for col in range(board_size):
            if zone == "north":
                score = 1.0 + (board_size - 1 - row) / max(1, board_size - 1)
            elif zone == "south":
                score = 1.0 + row / max(1, board_size - 1)
            elif zone == "east":
                score = 1.0 + col / max(1, board_size - 1)
            elif zone == "west":
                score = 1.0 + (board_size - 1 - col) / max(1, board_size - 1)
            else:
                distance = abs(row - midpoint) + abs(col - midpoint)
                score = 2.0 - distance / max(1.0, board_size - 1)
            evidence[(row, col)] = max(0.25, score)
    return evidence
