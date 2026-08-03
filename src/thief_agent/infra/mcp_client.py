"""Synchronous peer transport backed by the opponent's FastMCP server."""

import asyncio
import queue
import time

from fastmcp import Client

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
    ) -> None:
        self.opponent_url = opponent_url
        self.inboxes = inboxes
        self.connect_timeout = connect_timeout
        self.retry_interval = retry_interval
        self.reply_timeout = reply_timeout or connect_timeout

    def _call(self, tool: str, argument: dict) -> None:
        async def invoke() -> None:
            async with Client(self.opponent_url) as client:
                key = "payload" if tool == "submit_audit" else "message"
                await client.call_tool(tool, {key: argument})

        asyncio.run(invoke())

    def _send(self, tool: str, argument: dict) -> None:
        deadline = time.monotonic() + self.connect_timeout
        while True:
            try:
                self._call(tool, argument)
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
        self._send("receive_turn", message)

    def poll_turn(self, timeout: float | None = None) -> dict | None:
        return self._poll(self.inboxes.turns, timeout)

    def send_audit(self, payload: dict) -> None:
        self._send("submit_audit", payload)

    def poll_audit(self, timeout: float | None = None) -> dict | None:
        return self._poll(self.inboxes.audits, timeout)

    def send_control(self, message: dict) -> None:
        """Send an advisory control message to the opponent."""
        self._send("receive_control", message)

    def poll_control(self, timeout: float | None = None) -> dict | None:
        return self._poll(self.inboxes.controls, timeout)

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
