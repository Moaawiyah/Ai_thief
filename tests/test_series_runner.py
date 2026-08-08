"""SDK series composition is independently testable without a network peer."""

from types import SimpleNamespace

from thief_agent.peer.token_meter import step_usage
from thief_agent.sdk.providers import GatedLlm, StubLlm
from thief_agent.sdk.series_runner import play_series


class Config:
    shared = {}

    def get(self, key, default=None):
        return {"paths.logs_dir": "logs"}.get(key, default)


class Gate:
    def execute(self, function, *args, **kwargs):
        return function(*args, **kwargs)


class Provider:
    last_usage = {"model": "x", "total": 1}
    tokens_consumed = 1

    def send(self, prompt, timeout=None, schema=None):
        return prompt


def test_series_runner_connects_composes_and_delivers(monkeypatch, tmp_path):
    summary = {"winner": "thief", "result": "survival", "tokens_total": 2}
    series = SimpleNamespace(
        summaries=[summary], own_identity={"group_id": "thief-team"}, game_id="g1"
    )
    saved = []
    events = []

    class SDK:
        config = Config()
        _brain = None
        listener = events.append
        controls = None
        _workdir = tmp_path

        def _build_llm(self, stub):
            return "llm" if stub else "real"

        def connect(self):
            return "transport"

        def _save_log(self, result, report):
            saved.append((result, report))

    class Email:
        def __init__(self, config):
            self.config = config

        def send_report(self, report, subject):
            return {"sent": False, "subject": subject}

    monkeypatch.setattr("thief_agent.sdk.series_runner.validate_agreement", lambda _: None)
    def run_fake(*args, **kwargs):
        kwargs["listener"]({
            "type": "game_over",
            "summary": {"sub_game_number": 1},
        })
        return series

    monkeypatch.setattr("thief_agent.sdk.series_runner.run_series", run_fake)
    monkeypatch.setattr("thief_agent.sdk.series_runner.emit_series", lambda *a: {
        "final_result": {"winner_group": "thief-team"}
    })
    monkeypatch.setattr("thief_agent.sdk.series_runner.build_report", lambda *a, **k: {"game_id": "g1"})
    monkeypatch.setattr("thief_agent.sdk.series_runner.terms_from_config", lambda _: {})
    monkeypatch.setattr("thief_agent.sdk.series_runner.EmailSender", Email)
    outcome = play_series(SDK(), stub_llm=True)
    assert outcome["summary"] == summary
    assert outcome["series_result"]["winner_group"] == "thief-team"
    assert outcome["email"]["sent"] is False
    assert saved == [(summary, {"game_id": "g1"})]
    assert [event["type"] for event in events] == ["sub_game_over", "series_complete"]


def test_gated_provider_preserves_usage_and_stub_is_deterministic():
    provider = Provider()
    gated = GatedLlm(provider, Gate())
    assert gated.send("prompt") == "prompt"
    assert gated.tokens_consumed == 1
    assert gated.last_usage["model"] == "x"
    assert StubLlm().send("prompt")


def test_token_meter_reports_input_output_and_cumulative_delta():
    runtime = SimpleNamespace(llm=Provider(), hint_writer=None)
    usage, delta = step_usage(runtime, 0)
    assert usage == {"model": "x", "in": 0, "out": 0, "total": 1}
    assert delta == 1
