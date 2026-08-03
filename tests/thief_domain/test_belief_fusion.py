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
