"""One complete Thief sub-game against a remote Police peer."""

from thief_agent.domain.actions import hold
from thief_agent.domain.crypto import audit_records
from thief_agent.domain.own_state import OwnGameState
from thief_agent.domain.protocol import AuditPayload, ProtocolError, TurnMessage
from thief_agent.domain.rules import CAPTURE, SURVIVAL, TIMEOUT, GameRules
from thief_agent.domain.scent import ScentField
from thief_agent.infra.mcp_client import McpTransport
from thief_agent.infra.mcp_server import start_peer_server
from thief_agent.peer.handshake import (
    Negotiation,
    identity_from_config,
    terms_from_config,
    validate_config,
)
from thief_agent.peer.turns import seal_step, terminal_message, turn_message
from thief_agent.strategy import BeliefGrid, ThiefBrain


class ThiefRuntime:
    """Own the Thief state and drive the turn token over MCP."""

    def __init__(self, config, transport: McpTransport | None = None, brain=None):
        validate_config(config)
        self.config = config
        self.transport = transport or self._transport_from_config()
        self.terms = terms_from_config(config)
        size = config.get("board.size")
        start = tuple(config.get("positions.thief_start"))
        self.state = OwnGameState(start=start, board_size=size)
        self.belief = BeliefGrid.from_config(self.terms, config)
        self.scent = ScentField.from_terms(self.terms)
        self.rules = GameRules(
            max_steps=config.get("rules.max_steps"),
            survival_threshold=config.get("rules.survival_threshold"),
        )
        self.brain = brain or ThiefBrain()
        self.records: list[dict] = []
        self.peer_identity: dict = {}
        self._incoming_step = 0
        self._result: str | None = None

    def _transport_from_config(self) -> McpTransport:
        inboxes = start_peer_server(
            "thief",
            self.config.get("network.host", "127.0.0.1"),
            self.config.get("network.my_port"),
        )
        return McpTransport(
            self.config.get("network.opponent_url"),
            inboxes,
            connect_timeout=self.config.get("network.watchdog_timeout_seconds", 60),
            reply_timeout=self.config.get("network.response_timeout_seconds", 30),
            retry_interval=self.config.get("network.retry_interval_seconds", 0.25),
        )

    def run(self) -> dict:
        self._negotiate()
        self._take_turn()
        while self._result is None:
            incoming = self.transport.poll_turn(self._turn_timeout())
            if incoming is None:
                self._result = TIMEOUT
                break
            response = self._receive_turn(incoming)
            if self._result is not None:
                if self._result == CAPTURE:
                    self._send_terminal(response)
                break
            self._take_turn(response)
        audit = self._exchange_audit()
        return {
            "role": "thief",
            "result": self._result,
            "winner": "thief" if self._result == SURVIVAL else "police",
            "records": self.records,
            "audit": audit,
            "position": list(self.state.position),
            "steps": self.state.step_number,
        }

    def _negotiate(self) -> None:
        negotiation = Negotiation(terms_from_config(self.config), identity_from_config(self.config))
        peer = self.transport.exchange_agreement(negotiation.signed())
        negotiation.verify_peer(peer)
        self.peer_identity = negotiation.peer_identity

    def _take_turn(self, claim_response: dict | None = None) -> None:
        decision = self.brain.decide(self.state, self.belief)
        action = decision.action()
        if not self.state.apply_move(action):
            action = hold()
            self.state.apply_move(action)
        record = seal_step(self.state, action, decision)
        self.records.append(record)
        win = self.rules.survival_result(self.state)
        self.transport.send_turn(
            turn_message(
                record,
                decision.hint,
                claim_response,
                bool(win),
                smell_grid=self.scent.emit(self.state.position),
            )
        )
        if win:
            self._result = SURVIVAL

    def _receive_turn(self, raw: dict) -> dict | None:
        try:
            message = TurnMessage.from_dict(raw)
        except ProtocolError:
            self._result = "technical_loss"
            raise
        if message.sender != "police" or message.step != self._incoming_step + 1:
            self._result = "technical_loss"
            raise ProtocolError("unexpected Police turn sender or step")
        self._incoming_step = message.step
        # The Police has completed one turn. Predict its legal movement before
        # using the scent snapshot emitted with that turn as fresh evidence.
        self.belief.diffuse()
        self.belief.observe_smell(message.smell_grid)
        if message.barrier_placed:
            barrier = tuple(message.barrier_placed)
            if not self.state.board.in_bounds(barrier):
                raise ProtocolError("Police barrier is off the board")
            self.state.note_barrier(barrier)
            self.belief.exclude(barrier)
            if self.rules.barrier_captures(self.state, barrier) or self.rules.confinement_capture(self.state):
                self._result = CAPTURE
                return None
        if message.win_claim:
            self._result = SURVIVAL
            return None
        if message.capture_claim:
            claim = tuple(message.capture_claim)
            caught = self.rules.is_captured(self.state, claim)
            response = {"claim": list(claim), "caught": caught}
            if caught:
                self._result = CAPTURE
            return response
        return None

    def _send_terminal(self, claim_response: dict | None) -> None:
        if not self.records:
            return
        record = self.records[-1]
        self.transport.send_turn(terminal_message(record, self.state.step_number, claim_response))

    def _exchange_audit(self) -> dict:
        payload = AuditPayload("thief", self.records, self._result or TIMEOUT).to_dict()
        peer_raw = self.transport.exchange_audit(payload)
        own = audit_records(self.records)
        opponent = {"passed": False, "verified_steps": 0, "failed_steps": []}
        if peer_raw is not None:
            opponent = audit_records(AuditPayload.from_dict(peer_raw).records)
        return {"passed": own["passed"] and opponent["passed"], "own": own, "opponent": opponent}

    def _turn_timeout(self) -> float:
        return self.config.get("network.turn_timeout_seconds", 30)
