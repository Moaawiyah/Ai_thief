"""Headless heatmap color and geometry tests."""

from thief_agent.gui.palette import cell_rect, heat_color, role_color


def test_peak_heatmap_cell_is_redder_than_a_cool_cell():
    assert heat_color(1.0, 1.0) == "#ff3333"
    assert heat_color(0.0, 1.0) == "#ffffff"


def test_board_coordinates_are_row_major():
    assert cell_rect(2, 3) == (156, 104, 208, 156)
    assert role_color("thief") != role_color("police")
