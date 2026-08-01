"""Tests for terminal conditions evaluated by the Thief peer."""

from thief_agent.constants import Direction
from thief_agent.domain.actions import hold, move
from thief_agent.domain.own_state import OwnGameState
from thief_agent.domain.rules import SURVIVAL, GameRules


def rules(max_steps=35, survival_threshold=35):
    return GameRules(max_steps=max_steps, survival_threshold=survival_threshold)


def thief(start=(3, 3)):
    return OwnGameState(start=start, board_size=7)


class TestSurvival:
    def test_no_claim_before_the_threshold(self):
        state = thief()
        state.apply_move(move(Direction.N))
        assert rules(survival_threshold=3).survival_result(state) is None

    def test_claim_lands_exactly_on_the_threshold(self):
        state = thief()
        game_rules = rules(survival_threshold=2)
        state.apply_move(move(Direction.N))
        assert game_rules.survival_result(state) is None
        state.apply_move(move(Direction.S))
        assert game_rules.survival_result(state) == SURVIVAL

    def test_out_of_steps_tracks_the_move_ceiling(self):
        state = thief()
        game_rules = rules(max_steps=1)
        assert not game_rules.out_of_steps(state)
        state.apply_move(hold())
        assert game_rules.out_of_steps(state)


class TestCapture:
    def test_capture_claim_is_answered_honestly(self):
        state = thief()
        assert GameRules.is_captured(state, (3, 3))
        assert not GameRules.is_captured(state, (2, 3))

    def test_capture_claim_accepts_a_list_from_the_wire(self):
        assert GameRules.is_captured(thief(), [3, 3])


class TestBarrierCapture:
    def test_barrier_on_the_thief_cell_captures(self):
        assert GameRules.barrier_captures(thief(), (3, 3))

    def test_barrier_elsewhere_does_not_capture(self):
        assert not GameRules.barrier_captures(thief(), (3, 4))


class TestConfinementCapture:
    def test_confined_thief_is_captured(self):
        state = thief()
        for cell in [(2, 3), (4, 3), (3, 2), (3, 4)]:
            state.note_barrier(cell)
        assert GameRules.confinement_capture(state)

    def test_thief_with_one_escape_is_not_captured(self):
        state = thief()
        for cell in [(2, 3), (4, 3), (3, 2)]:
            state.note_barrier(cell)
        assert not GameRules.confinement_capture(state)
