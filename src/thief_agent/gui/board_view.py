"""Canvas heatmap and agent markers."""

import tkinter as tk

from thief_agent.gui.palette import (
    BANNER_FILL,
    BANNER_TEXT,
    BARRIER_FILL,
    CELL_PIXELS,
    GRID_LINE,
    VISITED_DOT,
    cell_rect,
    heat_color,
    role_color,
)

BANNER_HEIGHT = 22


class BoardView(tk.Canvas):
    """Full-redraw square board; every frame comes from one immutable snapshot."""

    def __init__(self, parent, board_size: int) -> None:
        self.board_size = board_size
        side = board_size * CELL_PIXELS
        super().__init__(
            parent,
            width=side,
            height=side,
            bg="white",
            highlightthickness=1,
            highlightbackground="#888888",
        )

    def render(self, view: dict) -> None:
        self.delete("all")
        self._draw_heatmap(view["belief"])
        for cell in view["visited"]:
            self._draw_dot(cell)
        for cell in view["barriers"]:
            self._draw_square(cell)
        opponent = view.get("opponent_position")
        if opponent is not None:
            self._draw_agent(opponent, view.get("opponent_role", "police"), 14)
        if view.get("position") is not None:
            self._draw_agent(view["position"], view["role"], 8)
        if view.get("message"):
            self._draw_banner(view["message"])

    def _draw_heatmap(self, belief: list[list[float]]) -> None:
        peak = max((cell for row in belief for cell in row), default=0.0)
        for row in range(self.board_size):
            for col in range(self.board_size):
                self.create_rectangle(
                    *cell_rect(row, col),
                    outline=GRID_LINE,
                    fill=heat_color(belief[row][col], peak),
                )

    def _draw_dot(self, cell) -> None:
        x0, y0, x1, y1 = cell_rect(*cell)
        self.create_oval(x0 + 21, y0 + 21, x1 - 21, y1 - 21, fill=VISITED_DOT, outline="")

    def _draw_square(self, cell) -> None:
        x0, y0, x1, y1 = cell_rect(*cell)
        self.create_rectangle(x0 + 4, y0 + 4, x1 - 4, y1 - 4, fill=BARRIER_FILL, outline="")

    def _draw_agent(self, cell, role: str, inset: int) -> None:
        x0, y0, x1, y1 = cell_rect(*cell)
        self.create_oval(
            x0 + inset,
            y0 + inset,
            x1 - inset,
            y1 - inset,
            fill=role_color(role),
            outline="black",
            width=2,
        )
        self.create_text((x0 + x1) // 2, (y0 + y1) // 2, text=role[:1].upper(), fill="white")

    def _draw_banner(self, message: str) -> None:
        width = self.board_size * CELL_PIXELS
        self.create_rectangle(0, 0, width, BANNER_HEIGHT, fill=BANNER_FILL, outline="")
        self.create_text(
            width // 2,
            BANNER_HEIGHT // 2,
            text=message,
            fill=BANNER_TEXT,
            font=("Helvetica", 10, "bold"),
        )
