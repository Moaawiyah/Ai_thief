"""Live Thief runtime mirrored in a Tk heatmap window."""

import queue
import threading
import time

from thief_agent.gui.game_mode import mode_and_model
from thief_agent.gui.live_apply import apply_event
from thief_agent.gui.live_controls import LiveControls
from thief_agent.gui.window import PeerWindow
from thief_agent.peer.controls import GameControls

DRAIN_INTERVAL_MS = 100
CLOCK_INTERVAL_MS = 1000
QUIT_GRACE_MS = 400


class LivePeerApp:
    def __init__(self, agent, controls=None) -> None:
        self._agent = agent
        self._controls = controls or GameControls()
        agent.listener = self._on_event
        agent.controls = self._controls
        self._events: queue.Queue = queue.Queue()
        self._summary: dict | None = None
        self._started_at: float | None = None
        self._title = f"THIEF - {agent.config.get('game.group_id', 'unnamed')} - port {agent.port}"
        self._window = PeerWindow(
            self._title,
            agent.config.require("board.size"),
            float(agent.config.get("gui.step_seconds", 0.0)),
        )
        mode, model = mode_and_model(agent.config)
        self._window.set_label("mode", mode)
        self._window.set_label("model", model)
        self._window.add_menu({"role": "thief", "verbal_mode": mode, "model": model})
        self._bar = LiveControls(self._window.root, self)

    def start(self) -> None:
        self._bar.mark_started()
        self._started_at = time.monotonic()
        self._window.set_turn(False, "STARTING - negotiating terms...")
        threading.Thread(target=self._worker, daemon=True, name="thief-runtime").start()
        self._window.root.after(CLOCK_INTERVAL_MS, self._tick_clock)

    def pause(self) -> None:
        self._controls.pause()
        self._window.set_turn(False, "PAUSED - the police clock is still running")

    def play(self) -> None:
        self._controls.play()
        self._window.set_turn(False, "RESUMED")

    def stop(self) -> None:
        self._controls.stop()
        self._window.set_turn(False, "STOPPING - abandoning this sub-game...")

    def quit(self) -> None:
        self._controls.stop()
        self._window.set_turn(False, "QUITTING...")
        self._window.root.after(QUIT_GRACE_MS, self._window.root.destroy)

    def _worker(self) -> None:
        try:
            self._summary = self._agent.play()
        except Exception as exc:  # noqa: BLE001 - show failures in the window
            self._events.put({"type": "error", "message": f"{type(exc).__name__}: {exc}"})

    def _on_event(self, event: dict) -> None:
        self._events.put(event)
        if event["type"] == "moved":
            time.sleep(max(0.0, self._window.speed.get()))

    def _drain(self) -> None:
        while not self._events.empty():
            event = self._events.get_nowait()
            apply_event(self._window, event)
            if event["type"] in ("game_over", "error"):
                self._started_at = None
                self._bar.mark_finished()
        self._window.root.after(DRAIN_INTERVAL_MS, self._drain)

    def _tick_clock(self) -> None:
        if self._started_at is not None:
            elapsed = int(time.monotonic() - self._started_at)
            self._window.root.title(f"{self._title} | {elapsed // 60:02d}:{elapsed % 60:02d}")
        self._window.root.after(CLOCK_INTERVAL_MS, self._tick_clock)

    def run(self) -> dict | None:
        self._window.set_turn(False, "READY - press Start")
        self._window.root.after(DRAIN_INTERVAL_MS, self._drain)
        self._window.root.mainloop()
        return self._summary
