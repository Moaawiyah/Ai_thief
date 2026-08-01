"""Tests for the Thief peer's authoritative private state."""

import pytest

from thief_agent.constants import Direction
from thief_agent.domain.actions import hold, move
from thief_agent.domain.own_state import OwnGameState


def thief(start=(3, 3), board_size=7):
    return OwnGameState(start=start, board_size=board_size)


class TestSetup:
    def test_starts_on_its_start_cell(self):
        state = thief()
        assert state.position == (3, 3)
        assert state.unique_cells == 1
        assert state.step_number == 0

    def test_rejects_a_start_cell_off_the_board(self):
        with pytest.raises(ValueError, match="off a 7x7 board"):
            thief(start=(7, 0))


class TestMovement:
    def test_move_updates_position_and_visited(self):
        state = thief()
        assert state.apply_move(move(Direction.N))
        assert state.position == (2, 3)
        assert state.unique_cells == 2

    def test_hold_keeps_position_and_unique_count(self):
        state = thief()
        assert state.apply_move(hold())
        assert state.position == (3, 3)
        assert state.unique_cells == 1
        assert state.step_number == 1

    def test_revisiting_a_cell_does_not_raise_the_unique_count(self):
        state = thief()
        state.apply_move(move(Direction.N))
        state.apply_move(move(Direction.S))
        assert state.position == (3, 3)
        assert state.unique_cells == 2

    def test_move_off_board_is_rejected_and_changes_nothing(self):
        state = thief(start=(0, 0))
        assert not state.apply_move(move(Direction.N))
        assert state.position == (0, 0)
        assert state.step_number == 0

    def test_move_into_a_declared_barrier_is_rejected(self):
        state = thief()
        state.note_barrier((2, 3))
        assert not state.apply_move(move(Direction.N))
        assert state.position == (3, 3)

    def test_unknown_action_type_is_rejected(self):
        state = thief()
        action = object.__new__(type("UnknownAction", (), {"move_type": "BARRIER"}))
        assert not state.apply_move(action)


class TestConfinement:
    def test_open_board_is_not_confinement(self):
        assert not thief().is_confined()

    def test_thief_walled_in_on_all_sides_is_confined(self):
        state = thief()
        for cell in [(2, 3), (4, 3), (3, 2), (3, 4)]:
            state.note_barrier(cell)
        assert state.is_confined()

    def test_board_edges_count_towards_confinement(self):
        state = thief(start=(0, 0))
        state.note_barrier((0, 1))
        state.note_barrier((1, 0))
        assert state.is_confined()


class TestLog:
    def test_log_records_each_thief_step(self):
        state = thief(start=(0, 0))
        state.apply_move(move(Direction.S))
        state.apply_move(hold())
        assert [entry["move"] for entry in state.log] == ["MOVE:S", "HOLD:-"]
        assert state.log[-1] == {
            "step": 2,
            "position": [1, 0],
            "move": "HOLD:-",
            "unique_cells": 2,
        }
