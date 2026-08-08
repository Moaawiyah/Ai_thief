"""Belief predict/update invariants and scent fusion."""

from thief_agent.strategy.belief import BeliefGrid


def total(belief):
    return round(sum(sum(row) for row in belief.as_matrix()), 9)


def test_scent_fusion_prefers_the_strongest_cell_and_stays_normalized():
    belief = BeliefGrid(7)
    belief.diffuse()
    belief.observe_smell({"1,1": 0.2, "5,5": 0.9})

    assert belief.most_likely() == (5, 5)
    assert total(belief) == 1.0


def test_prediction_spreads_only_to_stay_or_orthogonal_cells():
    belief = BeliefGrid(7)
    belief.observe_smell({"3,3": 0.9})
    belief.diffuse()
    matrix = belief.as_matrix()

    assert matrix[2][3] > matrix[2][2]
    assert matrix[3][2] > matrix[2][2]


def test_a_declared_barrier_gets_no_spread_mass():
    """Police cannot legally step onto a cell it has walled off, so a target
    in `barriers` must be skipped -- left unfiltered, probability keeps
    leaking onto cells Police can never reach and never gets reclaimed."""
    belief = BeliefGrid(7)
    belief.observe_smell({"3,3": 0.9})

    belief.diffuse(barriers={(2, 3)})

    assert belief.as_matrix()[2][3] == 0.0


def test_mass_is_conserved_even_when_every_target_is_blocked():
    """Walled in on every side, including staying put: mass has nowhere to
    go but stay -- it must not just vanish."""
    belief = BeliefGrid(7)
    belief.observe_smell({"3,3": 0.9})
    barriers = {(3, 3), (2, 3), (4, 3), (3, 2), (3, 4)}

    belief.diffuse(barriers=barriers)

    assert total(belief) == 1.0
    assert belief.as_matrix()[3][3] > 0.0


def test_empty_scent_does_not_reset_a_previous_belief():
    belief = BeliefGrid(7)
    belief.observe_smell({"6,6": 0.9})
    belief.diffuse()
    belief.observe_smell({})

    row, column = belief.most_likely()
    assert abs(row - 6) + abs(column - 6) <= 1


def test_excluding_every_cell_recovers_uniform_prior():
    belief = BeliefGrid(2)
    for cell in ((0, 0), (0, 1), (1, 0), (1, 1)):
        belief.exclude(cell)

    assert total(belief) == 1.0
    assert belief.as_matrix() == [[0.25, 0.25], [0.25, 0.25]]


def test_power_and_leak_default_to_the_shipped_values():
    belief = BeliefGrid.from_config({"board_size": 7}, {})

    assert belief._smell_power == 3.0
    assert belief._leak == 0.03


def test_power_and_leak_are_overridable_from_the_private_file():
    config = {"belief.smell_power": 3.0, "belief.leak": 0.1}

    belief = BeliefGrid.from_config({"board_size": 7}, config)

    assert belief._smell_power == 3.0
    assert belief._leak == 0.1
