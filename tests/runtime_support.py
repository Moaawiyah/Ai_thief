"""Deterministic Police test double and queue transport for runtime tests."""

import queue

from thief_agent.domain.crypto import CommitReveal
from thief_agent.domain.protocol import AuditPayload, TurnMessage
from thief_agent.peer.handshake import Negotiation, identity_from_config, terms_from_config


class QueueTransport:
    """A two-ended transport with the same API as McpTransport."""

    def __init__(self, incoming: queue.Queue, outgoing: queue.Queue):
        self.incoming = incoming
        self.outgoing = outgoing

    def exchange_agreement(self, message: dict) -> dict:
        self.outgoing.put(("agreement", message))
        kind, payload = self.incoming.get(timeout=5)
        assert kind == "agreement"
        return payload

    def send_turn(self, message: dict) -> None:
        self.outgoing.put(("turn", message))

    def poll_turn(self, timeout: float) -> dict | None:
        try:
            kind, payload = self.incoming.get(timeout=timeout)
        except queue.Empty:
            return None
        return payload if kind == "turn" else None

    def exchange_audit(self, payload: dict) -> dict | None:
        self.outgoing.put(("audit", payload))
        try:
            kind, response = self.incoming.get(timeout=5)
        except queue.Empty:
            return None
        return response if kind == "audit" else None


class PoliceDouble:
    """Police peer that only scripts protocol behavior; no production Police code."""

    def __init__(self, config, transport, scenario: str = "survival"):
        self.config = config
        self.transport = transport
        self.scenario = scenario
        self.records: list[dict] = []

    def run(self) -> dict:
        agreement = Negotiation(terms_from_config(self.config), identity_from_config(self.config))
        agreement.verify_peer(self.transport.exchange_agreement(agreement.signed()))
        incoming = self.transport.poll_turn(5)
        assert incoming is not None
        if self.scenario == "capture":
            self._send_turn(1, capture_claim=[4, 3])
            self.transport.poll_turn(5)
            result = "capture"
        else:
            step = 1
            while incoming is not None:
                message = TurnMessage.from_dict(incoming)
                if message.win_claim:
                    result = "survival"
                    break
                self._send_turn(step)
                step += 1
                incoming = self.transport.poll_turn(5)
            else:
                result = "timeout"
        peer_audit = self.transport.exchange_audit(
            AuditPayload("police", self.records, result).to_dict()
        )
        assert peer_audit is not None
        return {"result": result, "audit": peer_audit}

    def _send_turn(self, step: int, capture_claim: list | None = None) -> None:
        payload = {"step": step, "role": "police"}
        sealed = {"payload": payload, **CommitReveal.seal(payload)}
        self.records.append(sealed)
        message = TurnMessage(
            step=step,
            sender="police",
            hint="I am closing in.",
            smell_grid={},
            commit=sealed["commit"],
            timestamp=f"2026-01-01T00:00:0{step}Z",
            capture_claim=capture_claim,
        )
        self.transport.send_turn(message.to_dict())
