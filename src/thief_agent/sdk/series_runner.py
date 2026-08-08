"""Series orchestration and report emission for the public SDK."""

from thief_agent.infra.email_sender import EmailSender
from thief_agent.peer.sealing import terms_from_config, validate_agreement
from thief_agent.report.emit import emit_series
from thief_agent.report.report_writer import build_report
from thief_agent.sdk.series import run_series
from thief_agent.strategy import resolve_brain


def _series_listener(sdk):
    """Expose sub-game completion without making the GUI end the whole series."""
    if sdk.listener is None:
        return None

    def notify(event):
        if event.get("type") == "game_over":
            summary = event.get("summary", {})
            sdk.listener(
                {
                    **event,
                    "type": "sub_game_over",
                    "sub_game_number": summary.get("sub_game_number", 1),
                }
            )
            return
        sdk.listener(event)

    return notify


def play_series(sdk, stub_llm: bool = False) -> dict:
    """Play, emit, report, and optionally deliver the configured series."""
    validate_agreement(sdk.config)
    sdk._llm = sdk._build_llm(stub_llm)
    brain = sdk._brain or resolve_brain(sdk.config, sdk._llm)
    series = run_series(
        sdk.config,
        sdk.connect(),
        brain=brain,
        llm=sdk._llm,
        listener=_series_listener(sdk),
        controls=sdk.controls,
    )
    logs_dir = sdk._workdir / sdk.config.get("paths.logs_dir", "logs")
    result_json = emit_series(sdk.config, logs_dir, series)
    last = series.summaries[-1]
    report = build_report(last, sdk.config, terms=terms_from_config(sdk.config))
    sdk._save_log(last, report)
    winner = result_json["final_result"].get("winner_group") or last["winner"]
    subject = f"Police-Thief series result: winner {winner} (reported by thief)"
    email = EmailSender(sdk.config).send_report(report, subject)
    if sdk.listener is not None:
        sdk.listener(
            {
                "type": "series_complete",
                "result": result_json["final_result"],
                "num_sub_games": len(series.summaries),
            }
        )
    group_id = series.own_identity.get("group_id", "unknown-group")
    result_path = logs_dir / group_id / f"result_{series.game_id}.json"
    return {
        "summary": last,
        "report": report,
        "email": email,
        "summaries": series.summaries,
        "result": result_json,
        "series_result": result_json["final_result"],
        "log_path": str(result_path),
    }


__all__ = ["play_series"]
