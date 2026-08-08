"""Synchronous peer transport backed by the opponent's FastMCP server.

Turns go over the single `receive_turn` call, same as the Police peer's own
client: the Police server only ever exposes `negotiate` / `receive_turn` /
`submit_audit` / `receive_control`, never a separate `commit_turn` tool, so
calling one first against a real Police opponent burned the whole retry
budget on an unknown-tool failure and reported it as the opponent being
unreachable. Commit-reveal data (`commit`, `message_id`, `prior_commit`,
`move_reveal`, `expires_at_epoch`) still rides inside the TurnMessage payload
itself and is still checked end to end at the audit; only the extra
transport-level `commit_turn` round-trip is gone. This peer's own server still
exposes `commit_turn` for an opponent that wants the stricter two-phase path —
see `PeerInboxes.accept_reveal`, which accepts either.
"""

import asyncio
import contextlib
import queue
import time

from fastmcp import Client

from thief_agent.exceptions import ProviderError, SimulationError
from thief_agent.infra.mcp_server import PeerInboxes


class McpTransport:
    """Push messages to the opponent and poll this peer's inbound queues."""

    def __init__(
        self,
        opponent_url: str,
        inboxes: PeerInboxes,
        connect_timeout: float = 30.0,
        retry_interval: float = 0.25,
        reply_timeout: float | None = None,
        control_send_timeout: float = 2.0,
        gatekeeper=None,
    ) -> None:
        self.opponent_url = opponent_url
        self.inboxes = inboxes
        self.connect_timeout = connect_timeout
        self.retry_interval = retry_interval
        self.reply_timeout = reply_timeout or connect_timeout
        self.control_send_timeout = control_send_timeout
        self.gatekeeper = gatekeeper

    def _call(self, tool: str, argument: dict) -> None:
        async def invoke() -> None:
            async with Client(self.opponent_url) as client:
                key = "payload" if tool == "submit_audit" else "message"
                arguments = {} if tool == "health" else {key: argument}
                await client.call_tool(tool, arguments)

        try:
            asyncio.run(invoke())
        except Exception as exc:
            raise ProviderError(f"FastMCP {tool} call failed: {exc}") from exc

    def _send(self, tool: str, argument: dict, timeout: float | None = None) -> None:
        deadline = time.monotonic() + (timeout if timeout is not None else self.connect_timeout)
        while True:
            try:
                if self.gatekeeper is None:
                    self._call(tool, argument)
                else:
                    self.gatekeeper.execute(self._call, tool, argument)
                return
            except Exception as exc:
                if time.monotonic() >= deadline:
                    raise ConnectionError(
                        f"Opponent FastMCP server unreachable at {self.opponent_url}"
                    ) from exc
                time.sleep(self.retry_interval)

    def send_agreement(self, message: dict) -> None:
        self._send("negotiate", message)

    def exchange_agreement(self, message: dict) -> dict:
        """Send this peer's agreement and wait for the opponent's reply."""
        self.send_agreement(message)
        reply = self.poll_agreement(self.reply_timeout)
        if reply is None:
            raise TimeoutError("Opponent did not send a game agreement")
        return reply

    def poll_agreement(self, timeout: float | None = None) -> dict | None:
        return self._poll(self.inboxes.agreements, timeout)

    def send_turn(self, message: dict) -> None:
        """Reveal one turn over the single call every opponent implements."""
        self._send("receive_turn", message)

    def poll_turn(self, timeout: float | None = None) -> dict | None:
        return self._poll(self.inboxes.turns, timeout)

    def send_audit(self, payload: dict) -> None:
        self._send("submit_audit", payload)

    def poll_audit(self, timeout: float | None = None) -> dict | None:
        return self._poll(self.inboxes.audits, timeout)

    def send_control(self, message: dict) -> None:
        """Best-effort control send: a short timeout + suppressed error so a slow or
        departed opponent never stalls the game loop (control msgs are advisory)."""
        with contextlib.suppress(ConnectionError, SimulationError):
            self._send("receive_control", message, timeout=self.control_send_timeout)

    def poll_control(self) -> dict | None:
        """Non-blocking drain of one pending control message (None if empty)."""
        try:
            return self.inboxes.controls.get_nowait()
        except queue.Empty:
            return None

    def exchange_audit(self, payload: dict) -> dict | None:
        """Send an audit payload and wait briefly for the opponent's reveal."""
        self.send_audit(payload)
        return self.poll_audit(self.reply_timeout)

    def drain_inboxes(self) -> None:
        """Discard stale messages before starting a new handshake or game."""
        for inbox in (self.inboxes.turns, self.inboxes.audits, self.inboxes.controls):
            while True:
                try:
                    inbox.get_nowait()
                except queue.Empty:
                    break

    @staticmethod
    def _poll(inbox: queue.Queue[dict], timeout: float | None) -> dict | None:
        try:
            return inbox.get(timeout=timeout)
        except queue.Empty:
            return None
