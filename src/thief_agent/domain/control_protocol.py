"""Validated audit and control messages for the peer wire protocol."""

from dataclasses import MISSING, asdict, dataclass, fields
from typing import Any

from thief_agent.exceptions import ProtocolError

_ROLES = {"police", "thief"}


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
        if (
            isinstance(self.sub_game_number, bool)
            or not isinstance(self.sub_game_number, int)
            or self.sub_game_number < 1
            or not isinstance(self.status, str)
        ):
            raise ProtocolError("invalid control metadata")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ControlMessage":
        if not isinstance(data, dict):
            raise ProtocolError("control message must be an object")
        allowed = {field.name for field in fields(cls)}
        required = {field.name for field in fields(cls) if field.default is MISSING}
        if required - data.keys():
            raise ProtocolError(f"ControlMessage missing fields: {sorted(required - data.keys())}")
        try:
            return cls(**{key: value for key, value in data.items() if key in allowed})
        except TypeError as exc:
            raise ProtocolError(f"invalid ControlMessage: {exc}") from exc


__all__ = ["AuditPayload", "ControlMessage"]
