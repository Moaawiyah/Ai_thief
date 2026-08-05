"""GameControls: pause / play / stop / restart / quit for the live GUI.

Pause holds MY agent before it thinks (the opponent just waits for my message,
subject to its own turn timeout). Stop aborts my game entirely.
"""

import threading

PAUSE_POLL_SECONDS = 0.2

__all__ = ["GameControls"]


class GameControls:
    """Thread-safe control switches shared by GUI and runtime."""

    def __init__(self) -> None:
        self._resume = threading.Event()
        self._resume.set()  # running by default
        self._stop = threading.Event()
        self._restart = threading.Event()  # request a whole-series restart
        self._quit = threading.Event()  # clean quit (also notifies opponent)
        self._enable = threading.Event()  # opt in to the bidirectional control channel
        self._speed: float | None = None  # live step-time budget (sec); None -> config
        self._status_lock = threading.Lock()
        self._status = "READY"

    def set_speed(self, seconds: float) -> None:
        """Live override of the per-step time budget (GUI slider)."""
        self._speed = max(0.0, float(seconds))

    @property
    def speed(self) -> float | None:
        return self._speed

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    def pause(self) -> None:
        self._resume.clear()

    def play(self) -> None:
        self._resume.set()

    def stop(self) -> None:
        self._stop.set()
        self._resume.set()  # release any paused waiter so it can notice the stop

    def request_restart(self) -> None:
        self._restart.set()
        self._resume.set()

    def clear_restart(self) -> None:
        self._restart.clear()

    def request_quit(self) -> None:
        self._quit.set()
        self._resume.set()

    def request_enable(self) -> None:
        self._enable.set()

    @property
    def enable_requested(self) -> bool:
        return self._enable.is_set()

    def set_status(self, status: str) -> None:
        with self._status_lock:
            self._status = status

    @property
    def status(self) -> str:
        with self._status_lock:
            return self._status

    @property
    def paused(self) -> bool:
        return not self._resume.is_set()

    @property
    def restart_requested(self) -> bool:
        return self._restart.is_set()

    @property
    def quit_requested(self) -> bool:
        return self._quit.is_set()

    def wait_if_paused(self) -> None:
        while not self._stop.is_set() and not self._resume.wait(PAUSE_POLL_SECONDS):
            pass
