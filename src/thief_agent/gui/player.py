"""Live Thief runtime mirrored in a Tk heatmap window."""

import queue
import threading
import time

from thief_agent.exceptions import RestartSeries
from thief_agent.gui.game_mode import mode_and_model
from thief_agent.gui.live_apply import apply_event
from thief_agent.gui.live_controls import LiveControls
from thief_agent.gui.window import PeerWindow
from thief_agent.peer.controls import GameControls
from thief_agent.shared.git_info import code_revision
from thief_agent.shared.version import CODE_VERSION

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
        self._in_progress = False  # whether a worker thread currently owns _agent
        self._title = f"THIEF - {agent.config.get('game.group_id', 'unnamed')} - port {agent.port}"
        self._window = PeerWindow(
            self._title,
            agent.config.require("board.size"),
            float(agent.config.get("gui.step_seconds", 0.0)),
        )
        mode, model = mode_and_model(agent.config)
        self._window.set_label("mode", mode)
        self._window.set_label("model", model)
        self._window.add_menu(
            {
                "role": "thief",
                "verbal_mode": mode,
                "model": model,
                "code_version": CODE_VERSION,
                "commit": code_revision().get("commit", "unknown"),
            }
        )
        self._bar = LiveControls(self._window.root, self)

    def start(self) -> None:
        self._bar.mark_started()
        self._in_progress = True
        self._started_at = time.monotonic()
        total = self._agent.config.get("game.num_games", 1)
        self._window.set_label("game", f"1 / {total}")
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

    def restart(self) -> None:
        """Restart the match: mid-game, request it through the control channel
        so the active turn loop raises RestartSeries and this rebuilds in
        response (see _worker). Once a game has already ended there is no
        loop left to notice a request, so rebuild directly instead.
        """
        if self._in_progress:
            self._controls.request_restart()
            self._window.set_label("status", "restart requested...")
            return
        self._rebuild_and_start()

    def toggle_bidirectional(self) -> None:
        """Opt in to the bidirectional control channel (status/restart/quit)."""
        self._controls.request_enable()

    def _rebuild_and_start(self) -> None:
        """A new handshake and a new runtime, never a re-armed one."""
        self._in_progress = False
        self._agent.restart()
        self._controls = GameControls()
        if self._bar._bidi.get():
            self._controls.request_enable()
        self._agent.controls = self._controls
        self._summary = None
        self.start()

    def _worker(self) -> None:
        try:
            self._summary = self._agent.play_series()
        except RestartSeries:
            # Raised on this same worker thread, so agent.play() has already
            # unwound and returned control here before anything rebuilds --
            # never two runtimes racing. Dispatched via `after`: Tk is not
            # thread-safe and _rebuild_and_start touches the window.
            self._window.root.after(0, self._rebuild_and_start)
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
            if event["type"] in ("series_complete", "error"):
                self._started_at = None
                self._in_progress = False
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
