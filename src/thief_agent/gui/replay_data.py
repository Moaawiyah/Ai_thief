"""Pure saved-log normalization and commit verification for replay."""

from thief_agent.domain.crypto import CommitReveal, CryptoError

VERIFIED = "verified OK"
TAMPERED = "TAMPERED"
UNKNOWN = "-"


def normalize_log(log_data: dict) -> dict:
    body = log_data.get("summary") if isinstance(log_data.get("summary"), dict) else log_data
    return {
        "records": body.get("records") or log_data.get("records") or [],
        "history": body.get("history", []),
        "my_log": body.get("my_log", []),
        "role": body.get("role", "thief"),
        "result": body.get("result", UNKNOWN),
        "winner": body.get("winner") or "nobody",
        "group": body.get("group_name") or body.get("group_id", "unnamed"),
        "duration_seconds": body.get("duration_seconds", 0),
        "audit": body.get("audit") or {"passed": True, "verified_steps": 0},
    }


def verify_record(records: list, index: int) -> str:
    if index >= len(records):
        return UNKNOWN
    record = records[index]
    try:
        CommitReveal.verify(record["payload"], record["nonce"], record["commit"])
    except (CryptoError, KeyError, TypeError):
        return TAMPERED
    return VERIFIED


def move_labels(record: dict, verdict: str) -> dict:
    payload = record.get("payload") or {}
    commit = str(record.get("commit", UNKNOWN))
    return {
        "verdict": f"{payload.get('verdict', UNKNOWN)} (revealed)",
        "commit": f"{commit[:32]}... [{verdict}]",
    }


def opponent_positions(opponent_log: dict | None) -> list:
    if not opponent_log:
        return []
    return [entry["position"] for entry in normalize_log(opponent_log)["my_log"]]


def frozen_message(index: int, my_steps: int, opponent_steps: int) -> str | None:
    frozen = []
    if index >= my_steps:
        frozen.append("thief")
    if opponent_steps and index >= opponent_steps:
        frozen.append("police")
    return " | ".join(f"{role} track ended (frozen)" for role in frozen) or None
