"""Small coordinate helpers shared by belief and board-facing components."""

from thief_agent.constants import Cell


def in_bounds(cell: Cell, size: int) -> bool:
    """Return whether a two-dimensional cell belongs to a square grid."""
    return 0 <= cell[0] < size and 0 <= cell[1] < size


def parse_cell(key: str, size: int) -> Cell | None:
    """Parse the wire form ``"row,column"`` and reject malformed cells."""
    try:
        row_text, column_text = str(key).split(",")
        cell = (int(row_text), int(column_text))
    except (TypeError, ValueError):
        return None
    return cell if in_bounds(cell, size) else None


__all__ = ["in_bounds", "parse_cell"]
