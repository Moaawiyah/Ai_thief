"""Tests for the terminal conditions each peer evaluates on its own state."""

from police_thief.constants import Direction, Role
from police_thief.domain.actions import hold, move
from police_thief.domain.own_state import OwnGameState
from police_thief.domain.rules import SURVIVAL, GameRules


def rules(max_steps=35, survival_threshold=35):
    return GameRules(max_steps=max_steps, survival_threshold=survival_threshold)


def thief(start=(3, 3)):
    return OwnGameState(role=Role.THIEF, start=start, board_size=7)


class TestSurvival:
    def test_no_claim_before_the_threshold(self):
        state = thief()
        state.apply_move(move(Direction.N))
        assert rules(survival_threshold=3).thief_result(state) is None

    def test_claim_lands_exactly_on_the_threshold(self):
        state = thief()
        game_rules = rules(survival_threshold=2)
        state.apply_move(move(Direction.N))
        assert game_rules.thief_result(state) is None
        state.apply_move(move(Direction.S))
        assert game_rules.thief_result(state) == SURVIVAL

    def test_police_never_claims_survival(self):
        state = OwnGameState(role=Role.POLICE, start=(0, 0), board_size=7)
        state.apply_move(hold())
        assert rules(survival_threshold=1).thief_result(state) is None

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

    def test_claim_accepts_a_list_from_the_wire(self):
        assert GameRules.is_captured(thief(), [3, 3])


class TestBarrierCapture:
    """Appendix He, rule 46: walling the thief's own cell is a capture."""

    def test_barrier_on_the_thief_cell_captures(self):
        assert GameRules.barrier_captures(thief(), (3, 3))

    def test_barrier_elsewhere_does_not_capture(self):
        assert not GameRules.barrier_captures(thief(), (3, 4))

    def test_only_the_thief_can_be_captured_this_way(self):
        police = OwnGameState(role=Role.POLICE, start=(0, 0), board_size=7)
        assert not GameRules.barrier_captures(police, (0, 0))


class TestConfinementCapture:
    """Appendix He, rule 47: a thief with no legal step is captured."""

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

    def test_a_boxed_in_police_is_not_a_capture(self):
        state = OwnGameState(role=Role.POLICE, start=(0, 0), board_size=7)
        state.note_barrier((0, 1))
        state.note_barrier((1, 0))
        assert state.is_confined()
        assert not GameRules.confinement_capture(state)
