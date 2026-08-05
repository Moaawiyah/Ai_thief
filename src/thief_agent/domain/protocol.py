"""Validated JSON wire models shared with the Police peer."""

import re
from dataclasses import MISSING, asdict, dataclass, fields
from typing import Any

from thief_agent.exceptions import ProtocolError

__all__ = ["ProtocolError", "TurnMessage", "AuditPayload", "ControlMessage"]

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ROLES = {"police", "thief"}


def _cell(value: Any, field: str) -> list[int] | None:
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise ProtocolError(f"{field} must be a two-integer list")
    return value


@dataclass(frozen=True)
class TurnMessage:
    """A single public turn; private position and move stay inside `commit`."""

    step: int
    sender: str
    hint: str
    smell_grid: dict
    commit: str
    timestamp: str
    barrier_placed: list | None = None
    capture_claim: list | None = None
    claim_response: dict | None = None
    win_claim: dict | None = None
    message_id: str = ""  # idempotency key for commit/reveal
    expires_at_epoch: float = 0.0  # stale reveals are rejected
    move_reveal: str = ""  # action revealed after commit acknowledgement
    prior_commit: str = ""  # binds this turn to the previous local commitment
    schema_version: str = "1.1"  # explicit wire-contract version
    game_id: str = ""  # negotiated series identity
    sub_game_number: int = 1  # current role-alternating subgame

    def __post_init__(self) -> None:
        if isinstance(self.step, bool) or not isinstance(self.step, int) or self.step < 1:
            raise ProtocolError("step must be a positive integer")
        if self.sender not in _ROLES:
            raise ProtocolError("sender must be 'police' or 'thief'")
        if not isinstance(self.hint, str) or not isinstance(self.smell_grid, dict):
            raise ProtocolError("hint must be text and smell_grid must be an object")
        if not isinstance(self.commit, str) or not _HEX64.fullmatch(self.commit):
            raise ProtocolError("commit must be a lowercase SHA-256 hex digest")
        if not isinstance(self.timestamp, str) or not self.timestamp:
            raise ProtocolError("timestamp must be non-empty text")
        _cell(self.barrier_placed, "barrier_placed")
        _cell(self.capture_claim, "capture_claim")
        if self.claim_response is not None and not isinstance(self.claim_response, dict):
            raise ProtocolError("claim_response must be an object")
        if self.win_claim is not None and (
            not isinstance(self.win_claim, dict) or self.win_claim.get("type") != "survival"
        ):
            raise ProtocolError("win_claim must be {'type': 'survival'}")
        if not isinstance(self.message_id, str):
            raise ProtocolError("message_id must be text")
        if isinstance(self.expires_at_epoch, bool) or not isinstance(
            self.expires_at_epoch, (int, float)
        ):
            raise ProtocolError("expires_at_epoch must be a number")
        if not isinstance(self.move_reveal, str) or not isinstance(self.prior_commit, str):
            raise ProtocolError("move_reveal and prior_commit must be text")
        if not isinstance(self.schema_version, str) or not isinstance(self.game_id, str):
            raise ProtocolError("schema_version and game_id must be text")
        if (
            isinstance(self.sub_game_number, bool)
            or not isinstance(self.sub_game_number, int)
            or self.sub_game_number < 1
        ):
            raise ProtocolError("sub_game_number must be a positive integer")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TurnMessage":
        if not isinstance(data, dict):
            raise ProtocolError("turn message must be an object")
        required = {field.name for field in fields(cls) if field.default is MISSING}
        missing = required - data.keys()
        if missing:
            raise ProtocolError(f"TurnMessage missing fields: {sorted(missing)}")
        try:
            return cls(**data)
        except TypeError as exc:
            raise ProtocolError(f"invalid TurnMessage fields: {exc}") from exc


@dataclass(frozen=True)
class AuditPayload:
    """The end-of-game reveal exchanged by both peers."""

    sender: str
    records: list
    result_claim: str

    def __post_init__(self) -> None:
        if self.sender not in _ROLES or not isinstance(self.records, list):
            raise ProtocolError("audit sender or records are invalid")
        if self.result_claim not in {"capture", "survival", "timeout", "technical_loss"}:
            raise ProtocolError("unsupported audit result claim")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditPayload":
        if not isinstance(data, dict):
            raise ProtocolError("audit payload must be an object")
        try:
            return cls(**data)
        except (TypeError, KeyError) as exc:
            raise ProtocolError(f"invalid AuditPayload: {exc}") from exc


@dataclass(frozen=True)
class ControlMessage:
    """Optional out-of-band runtime status message."""

    kind: str
    sender: str
    sub_game_number: int = 1
    status: str = ""
    step_budget: float = 0.0
    payload: dict | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"enable", "status", "restart", "quit"}:
            raise ProtocolError("unsupported control kind")
        if self.sender not in _ROLES:
            raise ProtocolError("control sender must be 'police' or 'thief'")
        if self.sub_game_number < 1 or not isinstance(self.status, str):
            raise ProtocolError("invalid control metadata")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ControlMessage":
        if not isinstance(data, dict):
            raise ProtocolError("control message must be an object")
        allowed = {field.name for field in fields(cls)}
        try:
            return cls(**{key: value for key, value in data.items() if key in allowed})
        except TypeError as exc:
            raise ProtocolError(f"invalid ControlMessage: {exc}") from exc
