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


def test_series_events_keep_subgames_open_until_aggregate_result():
    window = FakeWindow()
    apply_event(
        window,
        {
            "type": "sub_game_over",
            "sub_game_number": 3,
            "summary": {"result": "survival", "winner": "thief"},
        },
    )
    assert window.labels["game"] == "3 complete"
    assert "starting next" in window.banner[1]

    apply_event(
        window,
        {
            "type": "series_complete",
            "num_sub_games": 6,
            "result": {"winner_group": "thief-team"},
        },
    )
    assert window.labels["game"] == "6 / 6 complete"
    assert "SERIES COMPLETE" in window.banner[1]
