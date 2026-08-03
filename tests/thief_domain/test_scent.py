"""Reference-compatible pheromone physics and wire behavior."""

import pytest

from thief_agent.domain.scent import ScentField


def scent_field(**overrides):
    terms = {
        "board_size": 7,
        "smell_grid_size": 5,
        "decay_per_step": 0.10,
        "emit_intensity": 0.9,
        "min_center_intensity": 0.5,
    }
    return ScentField.from_terms({**terms, **overrides})


def test_emission_matches_the_reference_radial_window():
    scent = scent_field()
    scent.deposit((3, 3))

    window = [
        [round(scent.intensity_at((row, column)), 2) for column in range(1, 6)]
        for row in range(1, 6)
    ]

    assert window == [
        [0.04, 0.14, 0.20, 0.14, 0.04],
        [0.14, 0.42, 0.62, 0.42, 0.14],
        [0.20, 0.62, 0.90, 0.62, 0.20],
        [0.14, 0.42, 0.62, 0.42, 0.14],
        [0.04, 0.14, 0.20, 0.14, 0.04],
    ]


def test_emit_decays_previous_trail_and_refreshes_current_cell():
    scent = scent_field()
    assert scent.emit((3, 3))["3,3"] == 0.9

    second = scent.emit((3, 4))

    assert second["3,4"] == 0.9
    assert second["3,3"] == 0.81


def test_wire_merge_uses_stronger_value_and_skips_junk():
    scent = scent_field()
    scent.absorb({"2,2": 0.4, "bad": 0.9, "8,8": 1.0, "1,1": "loud"})
    scent.absorb({"2,2": 0.7})

    assert scent.intensity_at((2, 2)) == 0.7
    assert scent.snapshot() == {"2,2": 0.7}


def test_decay_is_multiplicative_and_eventually_removes_trace():
    scent = scent_field()
    scent.deposit((3, 3))

    scent.decay_all()
    assert scent.intensity_at((3, 3)) == 0.81
    for _ in range(49):
        scent.decay_all()
    assert scent.snapshot() == {}


def test_invalid_field_and_emission_floor_are_rejected():
    with pytest.raises(ValueError, match="positive and odd"):
        scent_field(smell_grid_size=4)
    with pytest.raises(ValueError, match="below the agreed minimum"):
        scent_field().deposit((3, 3), intensity=0.4)
