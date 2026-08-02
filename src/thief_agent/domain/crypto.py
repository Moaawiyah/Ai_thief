"""Commit-reveal primitives used by the peer audit."""

import hashlib
import json
import secrets
from typing import Any


class CryptoError(ValueError):
    """Raised when a commitment or audit record does not verify."""


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
        nonce = secrets.token_hex(16)
        return {"nonce": nonce, "commit": cls.commit_of(payload, nonce)}

    @classmethod
    def verify(cls, payload: dict[str, Any], nonce: str, commit: str) -> None:
        actual = cls.commit_of(payload, nonce)
        if actual != commit:
            raise CryptoError("commitment does not match revealed payload")


def audit_records(records: list[dict]) -> dict:
    """Verify every revealed record and report all failed step numbers."""
    failed: list[int] = []
    for record in records:
        try:
            CommitReveal.verify(record["payload"], record["nonce"], record["commit"])
        except (CryptoError, KeyError, TypeError):
            failed.append(record.get("payload", {}).get("step", -1))
    return {
        "passed": not failed,
        "verified_steps": len(records) - len(failed),
        "failed_steps": failed,
    }
