"""Visual replay that rebuilds the Thief belief map from recorded scent."""

from thief_agent.gui.replay_controls import build_controls
from thief_agent.gui.replay_data import (
    frozen_message,
    move_labels,
    normalize_log,
    opponent_positions,
    verify_record,
)
from thief_agent.gui.window import PeerWindow
from thief_agent.strategy.belief import DEFAULT_SMELL_TRUST, BeliefGrid

DEFAULT_STEP_SECONDS = 0.5
MIN_TICK_MS = 50


class ReplayApp:
    def __init__(self, config, log_data: dict, opponent_log: dict | None = None, window=None) -> None:
        self._size = int(config.require("board.size"))
        self._trust = float(config.get("belief.smell_trust", DEFAULT_SMELL_TRUST))
        view = normalize_log(log_data)
        self._records = view["records"]
        self._history = view["history"]
        self._my_log = view["my_log"]
        self._role = view["role"]
        self._result, self._winner = view["result"], view["winner"]
        self._audit = view["audit"]
        self._opponent = opponent_positions(opponent_log)
        self._playing = False
        self._reset_state()
        self._window = window or PeerWindow(
            f"REPLAY - {view['group']} - {self._role} - {view['duration_seconds']}s",
            self._size,
            float(config.get("gui.step_seconds", DEFAULT_STEP_SECONDS)),
        )
        self._window.add_menu({"log_role": self._role, "result": self._result})
        self._window.set_label("mode", "Replay")

    def _reset_state(self) -> None:
        self._belief = BeliefGrid(self._size, self._trust)
        self._barriers: set = set()
        self._visited: set = set()
        self._index = 0

    def _total_steps(self) -> int:
        return max(len(self._my_log), len(self._history), len(self._opponent))

    def advance(self) -> None:
        total = self._total_steps()
        if self._index >= total:
            self._playing = False
            self._window.set_turn(False, f"REPLAY DONE: {self._result} - winner {str(self._winner).upper()}")
            return
        index = self._index
        self._apply_my_step(index)
        self._apply_opponent_step(index)
        self._render(index, total)
        self._index += 1

    def _apply_my_step(self, index: int) -> None:
        if index >= len(self._my_log):
            return
        entry = self._my_log[index]
        self._visited.add(tuple(entry["position"]))
        record = self._records[index] if index < len(self._records) else {}
        for key, value in move_labels(record, verify_record(self._records, index)).items():
            self._window.set_label(key, value)

    def _apply_opponent_step(self, index: int) -> None:
        if index >= len(self._history):
            return
        message = self._history[index]
        self._belief.diffuse()
        self._belief.observe_smell(message.get("smell_grid"))
        if message.get("barrier_placed"):
            self._barriers.add(tuple(message["barrier_placed"]))
        self._window.set_label("hint_in", f"step {index + 1}: {message.get('hint') or '(silent)'}")

    def _render(self, index: int, total: int) -> None:
        mine, theirs = len(self._my_log), len(self._opponent)
        self._window.render(
            {
                "role": self._role,
                "step": index + 1,
                "position": tuple(self._my_log[min(index, mine - 1)]["position"]) if mine else None,
                "visited": self._visited,
                "barriers": self._barriers,
                "belief": self._belief.as_matrix(),
                "opponent_position": tuple(self._opponent[min(index, theirs - 1)]) if theirs else None,
                "opponent_role": "police",
                "message": frozen_message(index, mine, theirs),
            }
        )
        self._window.set_label("status", f"step {index + 1}/{total} | audit {'PASSED' if self._audit.get('passed') else 'FAILED'}")

    def restart(self) -> None:
        self._reset_state()
        self._playing = False
        self._window.render({"role": self._role, "step": 0, "position": None, "visited": set(), "barriers": set(), "belief": self._belief.as_matrix()})
        self._window.set_turn(False, "RESTARTED - press Play")

    def goto(self, step: int) -> None:
        self._reset_state()
        for _ in range(max(1, min(step, self._total_steps()))):
            self.advance()

    def toggle(self) -> None:
        self._playing = not self._playing
        if self._playing:
            self._tick()

    def _tick(self) -> None:
        if not self._playing:
            return
        self.advance()
        self._window.root.after(max(MIN_TICK_MS, int(self._window.speed.get() * 1000)), self._tick)

    def run(self) -> None:
        self._window.set_turn(False, "REPLAY - press Play")
        build_controls(self, self._window.root)
        self._window.root.mainloop()
