"""Tests for the pure-Python Thief brain adapted from the reference policy."""

from thief_agent.constants import Direction, MoveType
from thief_agent.domain.actions import move
from thief_agent.domain.own_state import OwnGameState
from thief_agent.strategy import BeliefGrid, ThiefBrain


def test_brain_moves_away_from_the_believed_police():
    state = OwnGameState(start=(3, 3), board_size=7)
    belief = BeliefGrid(7)
    belief.observe((2, 3), weight=100)

    decision = ThiefBrain().decide(state, belief)

    assert decision.move_type is MoveType.MOVE
    assert decision.direction in (Direction.S, Direction.E, Direction.W)
    assert decision.action().direction is decision.direction


def test_brain_prefers_an_unvisited_tie_breaker():
    state = OwnGameState(start=(1, 1), board_size=3)
    state.apply_move(move(Direction.N))
    belief = BeliefGrid(3)
    belief.observe((0, 1), weight=100)

    decision = ThiefBrain().decide(state, belief)

    assert decision.direction is Direction.E
    assert (0, 1) in state.visited


def test_brain_holds_when_observed_barriers_remove_every_exit():
    state = OwnGameState(start=(1, 1), board_size=3)
    for cell in ((0, 1), (2, 1), (1, 0), (1, 2)):
        state.note_barrier(cell)

    decision = ThiefBrain().decide(state)

    assert decision == decision.__class__(MoveType.HOLD, None)


def test_belief_excludes_cells_and_returns_a_copy():
    belief = BeliefGrid(2)
    belief.observe((1, 1), weight=50)
    belief.exclude((1, 1))
    matrix = belief.as_matrix()
    matrix[0][0] = 99

    assert belief.most_likely() != (1, 1)
    assert belief.as_matrix()[0][0] != 99
