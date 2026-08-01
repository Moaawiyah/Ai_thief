"""Tests for the Thief Action value object and its shape rules."""

import pytest

from thief_agent.constants import Direction, MoveType
from thief_agent.domain.actions import Action, hold, move


class TestValidation:
    def test_move_requires_a_direction(self):
        with pytest.raises(ValueError, match="MOVE requires a direction"):
            Action(MoveType.MOVE)

    def test_hold_must_not_carry_a_direction(self):
        with pytest.raises(ValueError, match="must not carry a direction"):
            Action(MoveType.HOLD, Direction.N)

    def test_actions_are_frozen(self):
        with pytest.raises(AttributeError):
            move(Direction.N).direction = Direction.S


class TestConstructors:
    def test_helpers_build_the_expected_actions(self):
        assert move(Direction.N) == Action(MoveType.MOVE, Direction.N)
        assert hold() == Action(MoveType.HOLD, None)

    def test_string_form_is_loggable(self):
        assert str(move(Direction.S)) == "MOVE:S"
        assert str(hold()) == "HOLD:-"
