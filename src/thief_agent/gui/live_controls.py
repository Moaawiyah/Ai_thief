"""Start/pause/play/stop/quit/restart controls for a live Thief match."""

import tkinter as tk


class LiveControls:
    def __init__(self, root, app) -> None:
        bar = tk.Frame(root)
        bar.pack(pady=(0, 6))
        self.start = tk.Button(bar, text="Start", command=app.start)
        self.start.pack(side="left")
        self.pause = tk.Button(bar, text="Pause", command=app.pause, state="disabled")
        self.pause.pack(side="left", padx=(8, 0))
        self.play = tk.Button(bar, text="Play", command=app.play, state="disabled")
        self.play.pack(side="left")
        self.stop = tk.Button(bar, text="Stop", command=app.stop, state="disabled")
        self.stop.pack(side="left")
        self.quit = tk.Button(bar, text="Quit", command=app.quit)
        self.quit.pack(side="left", padx=(8, 0))
        self.restart = tk.Button(bar, text="Restart", command=app.restart)
        self.restart.pack(side="left", padx=(8, 0))
        self._bidi = tk.BooleanVar(value=False)
        self.bidi_check = tk.Checkbutton(
            bar, text="Bidirectional control", variable=self._bidi, command=app.toggle_bidirectional
        )
        self.bidi_check.pack(side="left", padx=(8, 0))

    def mark_started(self) -> None:
        self.start.config(state="disabled")
        for button in (self.pause, self.play, self.stop):
            button.config(state="normal")

    def mark_finished(self) -> None:
        for button in (self.pause, self.play, self.stop):
            button.config(state="disabled")
