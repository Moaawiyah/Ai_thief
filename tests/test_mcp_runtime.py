"""End-to-end one-game exchange over real FastMCP HTTP servers."""

import threading

from tests.runtime_support import PoliceDouble
from tests.test_runtime import config
from thief_agent.infra.mcp_client import McpTransport
from thief_agent.infra.mcp_server import start_peer_server
from thief_agent.peer.runtime import ThiefRuntime


def test_one_game_completes_over_real_fastmcp(tmp_path):
    thief_inboxes = start_peer_server("thief", "127.0.0.1", 18981)
    police_inboxes = start_peer_server("police", "127.0.0.1", 18982)
    thief_transport = McpTransport(
        "http://127.0.0.1:18982/mcp", thief_inboxes, connect_timeout=10
    )
    police_transport = McpTransport(
        "http://127.0.0.1:18981/mcp", police_inboxes, connect_timeout=10
    )
    cfg = config(tmp_path)
    thief = ThiefRuntime(cfg, thief_transport)
    police = PoliceDouble(cfg, police_transport)
    results = {}
    threads = [
        threading.Thread(target=lambda: results.setdefault("thief", thief.run())),
        threading.Thread(target=lambda: results.setdefault("police", police.run())),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive()
    assert results["thief"]["result"] == "survival"
    assert results["police"]["result"] == "survival"
    assert results["thief"]["audit"]["passed"] is True
