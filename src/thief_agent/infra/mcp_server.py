"""The Thief peer's FastMCP server and thread-safe inbound mailboxes."""

import queue
import socket
import threading

from fastmcp import FastMCP


class PeerInboxes:
    """Queues filled by FastMCP tools and consumed by the local peer."""

    def __init__(self) -> None:
        self.agreements: queue.Queue[dict] = queue.Queue()
        self.turns: queue.Queue[dict] = queue.Queue()
        self.audits: queue.Queue[dict] = queue.Queue()
        self.controls: queue.Queue[dict] = queue.Queue()


def _ensure_port_free(host: str, port: int) -> None:
    """Fail early when another process already owns the configured port."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
    except OSError as exc:
        raise OSError(f"FastMCP port {port} on {host} is already in use") from exc
    finally:
        probe.close()


def build_peer_server(role: str, inboxes: PeerInboxes) -> FastMCP:
    """Build this peer's public mailbox; no game state is exposed."""
    server = FastMCP(name=f"thief-agent-{role}")

    @server.tool
    def negotiate(message: dict) -> dict:
        """Receive a pre-game agreement from the opponent."""
        inboxes.agreements.put(message)
        return {"ok": True}

    @server.tool
    def receive_turn(message: dict) -> dict:
        """Receive one opaque turn message from the opponent."""
        inboxes.turns.put(message)
        return {"ok": True}

    @server.tool
    def submit_audit(payload: dict) -> dict:
        """Receive an end-of-game audit payload."""
        inboxes.audits.put(payload)
        return {"ok": True}

    @server.tool
    def receive_control(message: dict) -> dict:
        """Receive an optional status, restart, or quit signal."""
        inboxes.controls.put(message)
        return {"ok": True}

    return server


def start_peer_server(role: str, host: str, port: int) -> PeerInboxes:
    """Start FastMCP in a daemon thread and return its local mailboxes."""
    _ensure_port_free(host, port)
    inboxes = PeerInboxes()
    server = build_peer_server(role, inboxes)
    thread = threading.Thread(
        target=lambda: server.run(
            transport="http",
            host=host,
            port=port,
            show_banner=False,
            log_level="warning",
        ),
        daemon=True,
        name=f"fastmcp-{role}",
    )
    thread.start()
    return inboxes
