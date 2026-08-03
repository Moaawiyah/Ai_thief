"""Thread-safe pause, resume, and stop controls for the live GUI."""

import threading

PAUSE_POLL_SECONDS = 0.2


class GameControls:
    """Controls shared by Tk's main thread and the runtime worker."""

    def __init__(self) -> None:
        self._resume = threading.Event()
        self._resume.set()
        self._stop = threading.Event()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    def pause(self) -> None:
        self._resume.clear()

    def play(self) -> None:
        self._resume.set()

    def stop(self) -> None:
        self._stop.set()
        self._resume.set()

    def wait_if_paused(self) -> None:
        while not self._stop.is_set() and not self._resume.wait(PAUSE_POLL_SECONDS):
            pass
