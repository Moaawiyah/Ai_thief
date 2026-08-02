"""Tests for the FastMCP boundary's local mailbox behavior."""

import asyncio

from thief_agent.infra.mcp_server import PeerInboxes, build_peer_server


def test_server_tools_enqueue_opaque_messages():
    inboxes = PeerInboxes()
    server = build_peer_server("thief", inboxes)

    async def invoke_tools():
        assert {tool.name for tool in await server.list_tools()} == {
            "negotiate",
            "receive_turn",
            "submit_audit",
            "receive_control",
        }
        await server.call_tool("negotiate", {"message": {"game": "g1"}})
        await server.call_tool("receive_turn", {"message": {"step": 1}})
        await server.call_tool("submit_audit", {"payload": {"hash": "abc"}})
        await server.call_tool("receive_control", {"message": {"kind": "status"}})

    asyncio.run(invoke_tools())
    assert inboxes.agreements.get_nowait() == {"game": "g1"}
    assert inboxes.turns.get_nowait() == {"step": 1}
    assert inboxes.audits.get_nowait() == {"hash": "abc"}
    assert inboxes.controls.get_nowait() == {"kind": "status"}
