"""The Thief peer's own FastMCP server — there is no central server, ever.

The server is this agent's public mailbox: the opponent pushes negotiation
messages, two-phase commit/reveal turn messages, and audit payloads into
thread-safe inboxes that the local runtime consumes.
"""

import queue
import socket
import threading
import time

from fastmcp import FastMCP

from thief_agent.exceptions import SimulationError


def _ensure_port_free(host: str, port: int) -> None:
    """Fail early when another process already owns the configured port."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
    except OSError as exc:
        raise SimulationError(
            f"FastMCP port {port} on {host} is already in use - a previous peer is "
            f"probably still running, or another process owns the port. Stop it or "
            f"change network.my_port in this peer's config/thief/game.toml."
        ) from exc
    finally:
        probe.close()


class PeerInboxes:
    """Thread-safe mailboxes filled by MCP tools, drained by the runtime."""

    def __init__(self) -> None:
        self.agreements: queue.Queue[dict] = queue.Queue()
        self.turns: queue.Queue[dict] = queue.Queue()
        self.audits: queue.Queue[dict] = queue.Queue()
        self.controls: queue.Queue[dict] = queue.Queue()  # bidirectional control channel
        self.pending_commits: dict[str, dict] = {}
        self.delivered_ids: set[str] = set()
        self.commit_lock = threading.Lock()

    def accept_commit(self, message: dict) -> dict:
        """Store one idempotent commitment or reject a conflicting duplicate."""
        message_id = str(message.get("message_id", ""))
        if not message_id or not message.get("commit"):
            raise SimulationError("commit requires message_id and commit")
        with self.commit_lock:
            existing = self.pending_commits.get(message_id)
            if existing and existing.get("commit") != message.get("commit"):
                raise SimulationError("conflicting duplicate commitment")
            self.pending_commits[message_id] = dict(message)
        return {"ok": True, "message_id": message_id, "acknowledged": True}

    def accept_reveal(self, message: dict) -> dict:
        """Queue a fresh reveal exactly once, checking it against a prior
        commitment when one was made.

        Tolerant of peers that skip the commit phase entirely -- whether
        message_id is empty/absent, or set but never preceded by a
        `commit_turn` call (the Police peer's client sends this way: it has no
        `commit_turn` tool to call). A message_id is still deduped against
        replay either way, so idempotency holds even without the two-phase
        handshake; a genuine prior commitment, when there is one, is still
        checked in full.
        """
        message_id = str(message.get("message_id", ""))
        if not message_id:
            self.turns.put(message)
            return {"ok": True, "message_id": "", "revealed": True}
        with self.commit_lock:
            if message_id in self.delivered_ids:
                return {"ok": True, "message_id": message_id, "duplicate": True}
            pending = self.pending_commits.get(message_id)
            if pending is not None:
                if pending.get("commit") != message.get("commit"):
                    raise SimulationError("reveal commitment does not match acknowledged hash")
                envelope = ("schema_version", "game_id", "sub_game_number", "step", "sender")
                if any(key in pending and pending[key] != message.get(key) for key in envelope):
                    raise SimulationError("reveal envelope does not match acknowledged commitment")
                self.pending_commits.pop(message_id, None)
            expiry = float(message.get("expires_at_epoch", 0.0) or 0.0)
            if expiry and time.time() > expiry:
                raise SimulationError("reveal expired before delivery")
            self.delivered_ids.add(message_id)
        self.turns.put(message)
        return {"ok": True, "message_id": message_id, "revealed": True}


def build_peer_server(role: str, inboxes: PeerInboxes) -> FastMCP:
    """Build this peer's public mailbox; no game state is exposed."""
    server = FastMCP(name=f"thief-agent-{role}")

    @server.tool
    def health() -> dict:
        """Side-effect-free liveness and protocol-version probe."""
        return {"ok": True, "role": role, "schema_version": "1.1"}

    @server.tool
    def negotiate(message: dict) -> dict:
        """Receive a pre-game agreement from the opponent."""
        inboxes.agreements.put(message)
        return {"ok": True}

    @server.tool
    def commit_turn(message: dict) -> dict:
        """Lock a turn hash and acknowledge it before any action is revealed."""
        return inboxes.accept_commit(message)

    @server.tool
    def receive_turn(message: dict) -> dict:
        """Accept a reveal, requiring a matching prior commitment when one was sent."""
        return inboxes.accept_reveal(message)

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
