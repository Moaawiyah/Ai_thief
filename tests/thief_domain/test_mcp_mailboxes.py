"""Tests for the FastMCP boundary's local mailbox behavior."""

import asyncio

from thief_agent.infra.mcp_server import PeerInboxes, build_peer_server


def test_server_tools_enqueue_opaque_messages():
    inboxes = PeerInboxes()
    server = build_peer_server("thief", inboxes)

    async def invoke_tools():
        assert {tool.name for tool in await server.list_tools()} == {
            "health",
            "negotiate",
            "commit_turn",
            "receive_turn",
            "submit_audit",
            "receive_control",
        }
        health = await server.call_tool("health", {})
        assert health.structured_content == {"ok": True, "role": "thief", "schema_version": "1.1"}
        await server.call_tool("negotiate", {"message": {"game": "g1"}})
        await server.call_tool("receive_turn", {"message": {"step": 1}})
        await server.call_tool("submit_audit", {"payload": {"hash": "abc"}})
        await server.call_tool("receive_control", {"message": {"kind": "status"}})

    asyncio.run(invoke_tools())
    assert inboxes.agreements.get_nowait() == {"game": "g1"}
    assert inboxes.turns.get_nowait() == {"step": 1}
    assert inboxes.audits.get_nowait() == {"hash": "abc"}
    assert inboxes.controls.get_nowait() == {"kind": "status"}


def test_commit_then_reveal_two_phase_flow():
    inboxes = PeerInboxes()
    server = build_peer_server("thief", inboxes)
    commitment = {
        "message_id": "mid-1",
        "commit": "c" * 64,
        "step": 1,
        "sender": "police",
    }

    async def invoke_tools():
        ack = await server.call_tool("commit_turn", {"message": commitment})
        assert ack.structured_content == {"ok": True, "message_id": "mid-1", "acknowledged": True}
        reveal = await server.call_tool(
            "receive_turn", {"message": {**commitment, "move_reveal": "N"}}
        )
        assert reveal.structured_content == {"ok": True, "message_id": "mid-1", "revealed": True}
        duplicate = await server.call_tool(
            "receive_turn", {"message": {**commitment, "move_reveal": "N"}}
        )
        assert duplicate.structured_content == {
            "ok": True,
            "message_id": "mid-1",
            "duplicate": True,
        }

    asyncio.run(invoke_tools())
    assert inboxes.turns.get_nowait()["move_reveal"] == "N"
    assert inboxes.turns.empty()
