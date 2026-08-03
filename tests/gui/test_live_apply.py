"""Live event rendering can be tested without opening Tk."""

from thief_agent.gui.live_apply import apply_event


class FakeWindow:
    def __init__(self):
        self.labels = {}
        self.views = []
        self.banner = None

    def set_label(self, key, value):
        self.labels[key] = value

    def set_turn(self, mine, text=None):
        self.banner = (mine, text)

    def render(self, view):
        self.views.append(view)


def test_replayed_event_updates_status_without_changing_turn():
    window = FakeWindow()
    apply_event(window, {"type": "replay_ignored", "step": 2})

    assert "ignored" in window.labels["status"]
    assert window.banner is None


def test_game_over_event_reports_audit_and_winner():
    window = FakeWindow()
    apply_event(
        window,
        {
            "type": "game_over",
            "summary": {
                "result": "survival",
                "winner": "thief",
                "audit": {"passed": True, "own": {"verified_steps": 3}},
            },
        },
    )

    assert window.banner == (False, "GAME OVER: survival - winner THIEF")
    assert "PASSED" in window.labels["status"]
