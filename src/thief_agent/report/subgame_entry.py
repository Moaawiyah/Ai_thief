"""Build one sub-game's row in the aggregated result artifact."""

from thief_agent.domain import scoring
from thief_agent.report.artifact_helpers import ended_at
from thief_agent.report.artifacts import log_filename

__all__ = ["subgame_entry"]


def _roles(own_gid: str, opp_gid: str, own_role: str) -> dict:
    opp_role = "thief" if own_role == "police" else "police"
    return {own_gid: own_role, opp_gid: opp_role}


def subgame_entry(summary, game_id, own, opp, scoring_cfg) -> dict:
    """One sub-game's row in the result: roles, outcome, per-group score, audit."""
    own_gid = own.get("group_id", "unknown-group")
    opp_gid = opp.get("group_id", "unknown-opponent")
    roles = _roles(own_gid, opp_gid, summary["role"])
    n = summary["sub_game_number"]
    score = scoring.score_subgame(summary["result"], roles, scoring_cfg)
    winner = next((g for g, r in roles.items() if r == summary["winner"]), None)
    passed = summary["audit"]["passed"]
    return {
        "sub_game_number": n,
        "roles": roles,
        "started_at": summary["started_at"],
        "ended_at": ended_at(summary["started_at"], summary["duration_seconds"]),
        "result": summary["result"],
        "winner_group": winner,
        "tie": winner is None,
        "github_commit": {
            own_gid: own.get("github_commit", "unknown"),
            opp_gid: opp.get("github_commit", "unknown"),
        },
        "tokens": {own_gid: summary["tokens_total"], opp_gid: 0},
        "score": score,
        # each group writes into its OWN logs/<group_id>/ subfolder (roles alternate,
        # so group_id — not role — is the stable per-peer key that avoids collisions).
        "log_files": {
            own_gid: f"{own_gid}/{log_filename(game_id, n)}",
            opp_gid: f"{opp_gid}/{log_filename(game_id, n)}",
        },
        "audit": {"log_verified": passed, "tampered": not passed},
    }
