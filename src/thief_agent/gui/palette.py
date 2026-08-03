"""Tk-free colors and geometry for the heatmap."""

CELL_PIXELS = 52
ROLE_COLORS = {"thief": "#e67e22", "police": "#2980b9"}
UNKNOWN_ROLE_COLOR = "#555555"
GRID_LINE = "#cccccc"
VISITED_DOT = "#b0bec5"
BARRIER_FILL = "#263238"
BANNER_FILL = "#ffe082"
BANNER_TEXT = "#5d4037"
MAX_SATURATION = 0.8


def heat_color(probability: float, peak: float) -> str:
    if peak <= 0:
        return "#ffffff"
    level = min(1.0, max(0.0, probability / peak))
    green_blue = round(255 * (1 - MAX_SATURATION * level))
    return f"#ff{green_blue:02x}{green_blue:02x}"


def role_color(role: str) -> str:
    return ROLE_COLORS.get(role, UNKNOWN_ROLE_COLOR)


def cell_rect(row: int, col: int) -> tuple[int, int, int, int]:
    x0, y0 = col * CELL_PIXELS, row * CELL_PIXELS
    return x0, y0, x0 + CELL_PIXELS, y0 + CELL_PIXELS
