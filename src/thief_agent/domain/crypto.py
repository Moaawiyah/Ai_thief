"""Commit-reveal primitives used by the peer audit.

Every step this peer seals its true (state, move, verdict) under
commit = SHA256(canonical_json(payload) | nonce) and sends ONLY the commit.
Nonces are revealed at end-of-game audit; both sides then re-verify every
step, and the `prior_commit` chain (when present) is checked for
continuity — so no location or action can be rewritten after the fact.
"""

import hashlib
import json
import secrets
from typing import Any

from thief_agent.constants import NONCE_BYTES
from thief_agent.exceptions import CryptoError

__all__ = ["CryptoError", "CommitReveal", "audit_records"]


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class CommitReveal:
    """Seal payloads with SHA-256 and verify them after the game."""

    @staticmethod
    def commit_of(payload: dict[str, Any], nonce: str) -> str:
        if not isinstance(payload, dict) or not isinstance(nonce, str):
            raise CryptoError("payload and nonce have invalid types")
        return hashlib.sha256(f"{_canonical(payload)}|{nonce}".encode()).hexdigest()

    @classmethod
    def seal(cls, payload: dict[str, Any]) -> dict[str, str]:
        nonce = secrets.token_hex(NONCE_BYTES)
        return {"nonce": nonce, "commit": cls.commit_of(payload, nonce)}

    @classmethod
    def verify(cls, payload: dict[str, Any], nonce: str, commit: str) -> None:
        actual = cls.commit_of(payload, nonce)
        if not secrets.compare_digest(actual, commit):
            raise CryptoError("commitment does not match revealed payload")


def audit_records(records: list[dict]) -> dict:
    """Verify every revealed record, its `prior_commit` chain link, and
    report all failed step numbers."""
    failed: list[int] = []
    previous_commit: str | None = None
    for index, record in enumerate(records):
        step = -1
        try:
            payload = record["payload"]
            step = payload.get("step", -1)
            CommitReveal.verify(payload, record["nonce"], record["commit"])
            prior = payload.get("prior_commit")
            if index == 0 and prior:
                raise CryptoError("First record points to a missing predecessor")
            if index > 0 and "prior_commit" in payload and prior != previous_commit:
                raise CryptoError("Commit chain is broken")
        except (AttributeError, CryptoError, KeyError, TypeError):
            failed.append(step)
        previous_commit = record.get("commit") if isinstance(record, dict) else None
    return {
        "passed": not failed,
        "verified_steps": len(records) - len(failed),
        "failed_steps": failed,
    }
