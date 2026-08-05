"""One complete Thief sub-game against a remote Police peer."""

import time

from thief_agent.domain.own_state import OwnGameState
from thief_agent.domain.protocol import ProtocolError
from thief_agent.domain.rules import CAPTURE, TIMEOUT, GameRules
from thief_agent.domain.scent import ScentField
from thief_agent.infra.mcp_client import McpTransport
from thief_agent.infra.mcp_server import start_peer_server
from thief_agent.peer import handshake, summary, turn_sender
from thief_agent.peer.control_link import ControlLink
from thief_agent.peer.controls import GameControls
from thief_agent.peer.handshake import terms_from_config, validate_config
from thief_agent.peer.sealing import build_terminal_message
from thief_agent.peer.turn_handler import TurnHandler
from thief_agent.strategy import BeliefGrid, ThiefBrain
from thief_agent.strategy.talk import resolve_hint_writer


class ThiefRuntime:
    """Own the Thief state and drive the turn token over MCP."""

    def __init__(
        self,
        config,
        transport: McpTransport | None = None,
        brain=None,
        hint_writer=None,
        listener=None,
        controls=None,
        sub_game_number: int = 1,
        link=None,
    ):
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
        self.hint_writer = hint_writer or resolve_hint_writer(config)
        self.listener = listener
        self.controls = controls or GameControls()
        self.handler = TurnHandler(self.state, self.belief, self.rules)
        self.link = link or ControlLink(
            "thief", self.transport, self.controls, listener=self._notify
        )
        self.sub_game_number = sub_game_number
        self.records: list[dict] = []
        self.peer_identity: dict = {}
        self.game_id: str | None = None
        self.game_uid: str | None = None
        self._last_replayed = False
        self._last_police_hint = ""
        self.started_monotonic = time.monotonic()
        self.started_at = ""
        self.tokens_total = 0
        self._result: str | None = None

    @property
    def history(self) -> list[dict]:
        return self.handler.history

    @property
    def disputes(self) -> list[str]:
        return self.handler.disputes

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
        self.started_monotonic = time.monotonic()
        self._negotiate()
        self._notify({"type": "negotiated", "peer": self.peer_identity})
        self._take_turn()
        while self._result is None:
            self.controls.wait_if_paused()
            if self.controls.stopped:
                self._result = "technical_loss"
                break
            incoming = self.transport.poll_turn(self._turn_timeout())
            if incoming is None:
                self._result = TIMEOUT
                break
            response = self._receive_turn(incoming)
            if self._last_replayed:
                continue
            if self._result is not None:
                if self._result == CAPTURE:
                    self._send_terminal(response)
                break
            self._take_turn(response)
        return summary.finish(self)

    def _negotiate(self) -> None:
        handshake.negotiate(self)

    def _take_turn(self, claim_response: dict | None = None) -> None:
        turn_sender.take_turn(self, claim_response)

    def _receive_turn(self, raw: dict) -> dict | None:
        try:
            outcome = self.handler.process(raw)
        except ProtocolError:
            self._result = "technical_loss"
            raise
        self._last_replayed = outcome.replayed
        if outcome.result is not None:
            self._result = outcome.result
        self._last_police_hint = self.handler.history[-1]["hint"] if self.handler.history else ""
        return outcome.claim_response

    def _notify(self, event: dict) -> None:
        if self.listener is not None:
            self.listener({**event, "view": summary.snapshot(self)})

    def _send_terminal(self, claim_response: dict | None) -> None:
        if not self.records:
            return
        record = self.records[-1]
        message = build_terminal_message(record, self.state.step_number, claim_response)
        self.transport.send_turn(message.to_dict())

    def _turn_timeout(self) -> float:
        return self.config.get("network.turn_timeout_seconds", 30)
