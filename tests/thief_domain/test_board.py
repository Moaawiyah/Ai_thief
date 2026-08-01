"""Tests for pure board geometry: bounds, orthogonal steps, barriers."""

import pytest

from thief_agent.constants import Direction
from thief_agent.domain.board import Board


class TestGeometry:
    def test_rejects_non_positive_size(self):
        with pytest.raises(ValueError, match="must be positive"):
            Board(size=0)

    def test_in_bounds(self):
        board = Board(size=7)
        assert board.in_bounds((0, 0))
        assert board.in_bounds((6, 6))
        assert not board.in_bounds((7, 0))
        assert not board.in_bounds((-1, 3))

    def test_distance_is_manhattan(self):
        # Diagonals are illegal, so (0,0)->(2,3) really costs five steps.
        assert Board(size=7).distance((0, 0), (2, 3)) == 5

    def test_step_applies_the_direction(self):
        board = Board(size=7)
        assert board.step((3, 3), Direction.N) == (2, 3)
        assert board.step((3, 3), Direction.S) == (4, 3)
        assert board.step((3, 3), Direction.E) == (3, 4)
        assert board.step((3, 3), Direction.W) == (3, 2)

    def test_step_off_board_returns_none(self):
        board = Board(size=7)
        assert board.step((0, 0), Direction.N) is None
        assert board.step((6, 6), Direction.S) is None


class TestNoDiagonals:
    def test_direction_enum_has_only_four_members(self):
        # The specification fixes the move set; a diagonal must be unrepresentable.
        assert [d.value for d in Direction] == ["N", "S", "E", "W"]

    def test_centre_cell_has_exactly_four_neighbours(self):
        assert len(Board(size=7).neighbors((3, 3))) == 4

    def test_corner_cell_has_two_neighbours(self):
        assert sorted(Board(size=7).neighbors((0, 0))) == [(0, 1), (1, 0)]


class TestObservedBarriers:
    def test_barrier_blocks_a_step(self):
        assert Board(size=7).step((3, 3), Direction.N, barriers={(2, 3)}) is None

    def test_legal_moves_exclude_barriers(self):
        moves = Board(size=7).legal_moves((0, 0), barriers={(0, 1)})
        assert [cell for _, cell in moves] == [(1, 0)]
