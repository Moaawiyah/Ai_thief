"""Thief actions: one turn's move or hold, validated on construction."""

from dataclasses import dataclass

from thief_agent.constants import Direction, MoveType


@dataclass(frozen=True)
class Action:
    """A Thief action for one turn."""

    move_type: MoveType
    direction: Direction | None = None

    def __post_init__(self) -> None:
        if self.move_type is MoveType.MOVE and self.direction is None:
            raise ValueError("MOVE requires a direction")
        if self.move_type is MoveType.HOLD and self.direction is not None:
            raise ValueError("HOLD must not carry a direction")

    def __str__(self) -> str:
        return f"{self.move_type.value}:{self.direction.value if self.direction else '-'}"


def move(direction: Direction) -> Action:
    """Step one cell in `direction`."""
    return Action(MoveType.MOVE, direction)


def hold() -> Action:
    """Stay put for this turn."""
    return Action(MoveType.HOLD)
