"""Regression coverage for the Thief's first turn against a real Police peer.

Police's client has no `commit_turn` tool: it only ever exposes `negotiate` /
`receive_turn` / `submit_audit` / `receive_control`. `send_turn` used to call
`commit_turn` first whenever the message carried a `message_id` -- which every
real turn does (`peer/sealing.py::build_turn_message`) -- so the very first
turn against a real Police opponent burned the whole retry budget on an
unknown tool and surfaced as "opponent unreachable" instead of the protocol
mismatch it actually was.
"""

import socket
import threading

from fastmcp import FastMCP

from thief_agent.domain.protocol import TurnMessage
from thief_agent.infra.mcp_client import McpTransport
from thief_agent.infra.mcp_server import PeerInboxes


class _Recorder:
    """Stands in for the MCP call, recording which tool would have been hit."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, tool: str, arguments: dict) -> None:
        self.calls.append((tool, arguments))


def _turn_message(message_id: str) -> dict:
    return TurnMessage(
        step=1,
        sender="thief",
        hint="",
        smell_grid={},
        commit="c" * 64,
        timestamp="2026-01-01T00:00:00Z",
        message_id=message_id,
    ).to_dict()


def test_send_turn_never_calls_commit_turn_even_with_a_message_id():
    """The direct regression test for the client: a real turn always carries a
    message_id, so this used to unconditionally reach for a tool the Police
    peer's server never implements."""
    transport = McpTransport("http://127.0.0.1:1/mcp", PeerInboxes())
    transport._call = _Recorder()

    transport.send_turn(_turn_message("mid-1"))

    assert [tool for tool, _ in transport._call.calls] == ["receive_turn"]


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _start_police_shaped_server(host: str, port: int) -> PeerInboxes:
    """A server exposing exactly the Police peer's real tool set -- no
    `commit_turn` -- so the test fails the way the real bug did if it regresses."""
    inboxes = PeerInboxes()
    server = FastMCP(name="police-shaped-double")

    @server.tool
    def negotiate(message: dict) -> dict:
        inboxes.agreements.put(message)
        return {"ok": True}

    @server.tool
    def receive_turn(message: dict) -> dict:
        inboxes.turns.put(message)
        return {"ok": True}

    @server.tool
    def submit_audit(payload: dict) -> dict:
        inboxes.audits.put(payload)
        return {"ok": True}

    thread = threading.Thread(
        target=lambda: server.run(
            transport="http", host=host, port=port, show_banner=False, log_level="warning"
        ),
        daemon=True,
        name="police-shaped-double",
    )
    thread.start()
    return inboxes


def test_the_first_turn_reaches_a_police_shaped_server_with_no_commit_turn_tool():
    """End to end over a real socket: without the fix this call raises
    ConnectionError after burning the whole connect_timeout on commit_turn."""
    host = "127.0.0.1"
    port = _free_port()
    inboxes = _start_police_shaped_server(host, port)
    transport = McpTransport(f"http://{host}:{port}/mcp", PeerInboxes(), connect_timeout=5)

    transport.send_turn(_turn_message("mid-2"))

    delivered = inboxes.turns.get(timeout=5)
    assert delivered["message_id"] == "mid-2"
    assert delivered["commit"] == "c" * 64
