"""Standardized artifacts, Hebrew report output, and safe email delivery."""

import json

from thief_agent.infra.email_sender import EmailSender
from thief_agent.report.artifact_helpers import (
    canonical_sha256,
    ended_at,
    group_block,
    hardware_spec,
    links,
    tokens_series,
)
from thief_agent.report.artifacts import (
    build_config_artifact,
    build_declaration,
    build_log,
    build_result,
)
from thief_agent.report.emit import emit_series
from thief_agent.report.report_writer import build_report, consensus_signature
from thief_agent.sdk.series import SeriesResult
from thief_agent.shared.config import ConfigManager


def identity(group_id, role):
    return {
        "group_id": group_id,
        "group_name": f"{role.title()} team",
        "members": ["member-1"],
        "repos": {role: f"https://github.com/example/{role}"},
        "mcp_servers": {role: f"https://example.test/{role}"},
        "llm_model": "template",
        "spec": {
            "cpu_type": "cpu", "cpu_freq_mhz": 1, "cpu_cores": 2,
            "ram_gb": 4, "gpu_type": "gpu", "vram_gb": 1,
        },
        "github_commit": "abc",
    }


def summary():
    message = {
        "step": 1, "timestamp": "2026-01-01T00:00:00+00:00", "sender": "thief",
        "hint": "A quiet alley", "smell_grid": {}, "barrier_placed": None,
        "commit": "c" * 64,
    }
    return {
        "role": "thief", "group_name": "Thief team", "sub_game_number": 1,
        "result": "survival", "winner": "thief", "steps": 1,
        "started_at": "2026-01-01T00:00:00+00:00", "duration_seconds": 2,
        "tokens_total": 7, "records": [], "history": [message],
        "audit": {"passed": True, "own": {"verified_steps": 1, "failed_steps": []}},
        "state_transitions": [],
        "belief_log": [{"step": 1, "smell_grid": {}, "belief": [[1.0]]}],
    }


def test_artifact_helpers_and_builders_are_canonical():
    own, opp = identity("thief-team", "thief"), identity("police-team", "police")
    assert links("g1")["config"] == "config_g1_g<NN>.json"
    assert len(canonical_sha256({"b": 1, "a": 2})) == 64
    assert ended_at("2026-01-01T00:00:00+00:00", 2).endswith("00:00:02+00:00")
    assert ended_at("bad", 2) == "bad"
    assert hardware_spec(own["spec"])["gpu_model"] == "gpu"
    assert tokens_series([{"tokens": {"thief-team": 7}}], ["thief-team"]) == {"thief-team": 7}
    declaration = build_declaration("g1", "u1", "UTC", "start", "end", 1, 100, own, opp)
    config = build_config_artifact({"schema_version": "1.3"}, "g1", "u1", 1)
    log = build_log(summary(), "g1", "u1", "thief-team", "police-team")
    result = build_result("g1", "u1", ["police-team", "thief-team"], [], {}, "x")
    assert declaration["groups"]["group_1"]["group_id"] == "thief-team"
    assert config["config_name"] == "config_g1_g01.json"
    assert log["summary"]["tokens_total"] == 7
    assert result["num_sub_games"] == 0


def test_group_block_reads_our_own_spec_key():
    own = identity("thief-team", "thief")

    assert group_block(own)["hardware_spec"]["gpu_model"] == "gpu"


def test_group_block_also_accepts_the_police_peers_differently_named_key():
    """A real series crashed here: the Police repo's own identity payload
    names this field `hardware_spec`, not `spec` -- nothing in the (unsigned)
    identity block ever pinned the two repos to agree on that name."""
    opponent = identity("police-team", "police")
    opponent["hardware_spec"] = opponent.pop("spec")

    assert group_block(opponent)["hardware_spec"]["gpu_model"] == "gpu"


def test_group_block_degrades_to_empty_fields_rather_than_crash():
    """Neither key present at all -- some future, differently-shaped
    opponent -- must still produce a report instead of failing the series."""
    opponent = identity("mystery-team", "police")
    del opponent["spec"]

    assert group_block(opponent)["hardware_spec"]["gpu_model"] is None


def test_emit_series_writes_named_files_and_report(tmp_path):
    config = ConfigManager("config/thief")
    own, opp = identity("thief-team", "thief"), identity("police-team", "police")
    series = SeriesResult([summary()], own, opp, "g1", "u1")
    result = emit_series(config, tmp_path, series)
    folder = tmp_path / "thief-team"
    assert (folder / "declaration_g1.json").exists()
    assert (folder / "config_g1_g01.json").exists()
    assert (folder / "log_g1_g01.json").exists()
    record = json.loads((folder / "record_g1_g01.json").read_text(encoding="utf-8"))
    assert record["belief_log"] == summary()["belief_log"]
    assert result["final_result"]["tokens_total_series"]["thief-team"] == 7
    report = build_report(summary(), config, {"board_size": 7})
    assert report["סך_טוקנים_שנצרכו"] == 7
    assert len(report["חתימת_קונסנזוס_משותפת"]) == 64
    assert consensus_signature({"a": 1}) == consensus_signature({"a": 1})


def test_email_is_disabled_or_writes_a_local_draft(tmp_path):
    config = ConfigManager("config/thief")
    sender = EmailSender(config)
    assert sender.send_report({"game_id": "g1"}, "subject")["reason"] == "disabled"
    config.override("email.enabled", True)
    config.override("email.mode", "draft")
    config.override("email.outbox_dir", str(tmp_path))
    draft = sender.send_report({"game_id": "g1"}, "subject")
    assert draft["mode"] == "draft"
    assert (tmp_path / "result_g1.eml").exists()
