"""Wire the four JSON artifact builders to disk for a whole series.

`emit_series` writes ONE declaration + result and a per-sub-game config + log,
all named from the shared game_id, and returns the result dict (for emailing).
Per-group scores come from `domain.scoring`; the two peers derive identical
sub-game entries (same roles/result/scores), so their result files agree.
"""

import json
from pathlib import Path

from thief_agent.domain import scoring
from thief_agent.report.artifact_helpers import ended_at
from thief_agent.report.artifact_schemas import DEFAULT_TIMEZONE
from thief_agent.report.artifacts import (
    build_config_artifact,
    build_declaration,
    build_log,
    build_result,
    config_filename,
    declaration_filename,
    log_filename,
    record_filename,
    result_filename,
)
from thief_agent.report.report_writer import consensus_signature
from thief_agent.report.subgame_entry import subgame_entry

__all__ = ["emit_series"]

_DEFAULT_SCORING = {
    "capture_cop": 20,
    "capture_thief": 5,
    "survival_cop": 5,
    "survival_thief": 10,
    "tie_score": 2,
}
_DEFAULT_TOKEN_BUDGET = 200000


def _write(logs_dir, filename: str, data: dict) -> Path:
    out = Path(logs_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _scoring(config) -> dict:
    return config.get("scoring") or dict(_DEFAULT_SCORING)


def _max_tokens(config) -> int:
    league = config.shared.get("network_and_league", {}) if config.shared else {}
    return league.get("token_budget_per_series", _DEFAULT_TOKEN_BUDGET)


def emit_series(config, logs_dir, series) -> dict:
    """Write all four artifacts for `series` and return the result dict."""
    own = series.own_identity
    opp = series.peer_identity or own
    own_gid = own.get("group_id", "unknown-group")
    opp_gid = opp.get("group_id", "unknown-opponent")
    game_id = series.game_id or f"{own_gid}-vs-{opp_gid}"
    game_uid = series.game_uid or "0"
    scoring_cfg = _scoring(config)
    summaries = series.summaries
    first, last = summaries[0], summaries[-1]
    # This peer writes its four files into its OWN group subfolder so that, on a
    # single machine, both peers' declaration/config/log/result coexist (they share
    # game_id, and roles alternate, so group_id is the stable per-peer discriminator).
    own_dir = Path(logs_dir) / own_gid

    _write(
        own_dir,
        declaration_filename(game_id),
        build_declaration(
            game_id,
            game_uid,
            DEFAULT_TIMEZONE,
            first["started_at"],
            ended_at(last["started_at"], last["duration_seconds"]),
            len(summaries),
            _max_tokens(config),
            own,
            opp,
        ),
    )

    sub_games = []
    for summary in summaries:
        n = summary["sub_game_number"]
        _write(
            own_dir,
            config_filename(game_id, n),
            build_config_artifact(config.shared, game_id, game_uid, n),
        )
        _write(
            own_dir,
            log_filename(game_id, n),
            build_log(summary, game_id, game_uid, own_gid, opp_gid),
        )
        # The raw runtime summary, belief_log included -- not one of the four
        # schema-fixed artifacts, but the only place the Bayes-filter trail
        # actually lands on disk.
        _write(own_dir, record_filename(game_id, n), summary)
        sub_games.append(subgame_entry(summary, game_id, own, opp, scoring_cfg))

    agg = scoring.aggregate([sg["score"] for sg in sub_games], scoring_cfg.get("tie_score", 2))
    # The mutual signature must be BYTE-IDENTICAL for both peers, so hash only the
    # symmetric outcome (roles/result/score/aggregate) — never per-peer tokens or
    # wall-clock timestamps, which legitimately differ between the two peers.
    symmetric = {
        "game_id": game_id,
        "aggregate": agg,
        "sub_games": [
            {
                "sub_game_number": sg["sub_game_number"],
                "roles": sg["roles"],
                "result": sg["result"],
                "winner_group": sg["winner_group"],
                "score": sg["score"],
            }
            for sg in sub_games
        ],
    }
    mutual = consensus_signature(symmetric)
    result = build_result(game_id, game_uid, sorted([own_gid, opp_gid]), sub_games, agg, mutual)
    _write(own_dir, result_filename(game_id), result)
    return result
