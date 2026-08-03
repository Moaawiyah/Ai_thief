"""Shared Tk window chrome for live Thief play and replay."""

import tkinter as tk

from thief_agent.gui.board_view import BoardView

MY_TURN_COLOR = "#2ecc71"
WAITING_COLOR = "#95a5a6"
PANEL_ROWS = (
    ("step", "Step"),
    ("mode", "Verbal mode"),
    ("model", "Model"),
    ("hint_in", "Police says"),
    ("hint_out", "My hint"),
    ("verdict", "Why I moved"),
    ("commit", "My commit"),
    ("status", "Status"),
)


class PeerWindow:
    """Window that only renders snapshots and event labels."""

    def __init__(self, title: str, board_size: int, speed: float) -> None:
        self.root = tk.Tk()
        self.root.title(title)
        self.banner = tk.Label(
            self.root, text="WAITING...", bg=WAITING_COLOR, fg="white", font=("Helvetica", 14, "bold")
        )
        self.banner.pack(fill="x")
        body = tk.Frame(self.root)
        body.pack(padx=8, pady=8)
        self.board = BoardView(body, board_size)
        self.board.pack(side="left")
        self.labels: dict[str, tk.Label] = {}
        self.speed = tk.DoubleVar(value=speed)
        panel = tk.Frame(body)
        panel.pack(side="left", fill="y", padx=(10, 0))
        for key, caption in PANEL_ROWS:
            tk.Label(panel, text=f"{caption}:", font=("Helvetica", 9, "bold"), anchor="w").pack(fill="x")
            self.labels[key] = tk.Label(panel, text="-", anchor="w", wraplength=300, justify="left")
            self.labels[key].pack(fill="x", pady=(0, 6))
        tk.Label(panel, text="Seconds per step:", font=("Helvetica", 9, "bold"), anchor="w").pack(fill="x")
        tk.Scale(panel, from_=0.0, to=10.0, resolution=0.1, orient="horizontal", variable=self.speed).pack(fill="x")

    def add_menu(self, about: dict) -> None:
        menubar = tk.Menu(self.root)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=lambda: self._show_about(about))
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def _show_about(self, about: dict) -> None:
        top = tk.Toplevel(self.root)
        top.title("About - Thief Agent")
        tk.Label(top, text="Thief Agent\n" + "\n".join(f"{key}: {value}" for key, value in about.items()), justify="left", padx=14, pady=12).pack()
        tk.Button(top, text="Close", command=top.destroy).pack(pady=(0, 10))

    def set_turn(self, mine: bool, text: str | None = None) -> None:
        self.banner.config(
            bg=MY_TURN_COLOR if mine else WAITING_COLOR,
            text=text or ("MY TURN - deciding..." if mine else "WAITING for the police..."),
        )

    def set_label(self, key: str, value: str) -> None:
        if key in self.labels:
            self.labels[key].config(text=value)

    def render(self, view: dict) -> None:
        self.board.render(view)
        self.set_label("step", str(view["step"]))
