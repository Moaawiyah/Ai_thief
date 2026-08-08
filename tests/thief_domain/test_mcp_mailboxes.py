"""Tests for the FastMCP boundary's local mailbox behavior."""

import asyncio

import pytest

from thief_agent.exceptions import SimulationError
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


def test_a_reveal_with_a_message_id_but_no_prior_commit_is_accepted_directly():
    """The Police peer's client has no `commit_turn` tool to call, so a real
    match's every turn arrives this way: message_id set, no commitment ever
    registered. It must be delivered, not rejected as missing one."""
    inboxes = PeerInboxes()

    ack = inboxes.accept_reveal({"message_id": "mid-2", "commit": "c" * 64, "step": 1})

    assert ack == {"ok": True, "message_id": "mid-2", "revealed": True}
    assert inboxes.turns.get_nowait()["message_id"] == "mid-2"


def test_a_message_id_is_still_deduped_without_a_prior_commit():
    """Dropping the two-phase requirement must not drop the idempotency it
    also provided: a resent turn is still recognised as the same one."""
    inboxes = PeerInboxes()
    message = {"message_id": "mid-3", "commit": "c" * 64, "step": 1}

    inboxes.accept_reveal(message)
    duplicate = inboxes.accept_reveal(message)

    assert duplicate == {"ok": True, "message_id": "mid-3", "duplicate": True}
    assert inboxes.turns.qsize() == 1


def test_an_expired_reveal_is_rejected_even_without_a_prior_commit():
    """Commit-reveal security is unchanged: a stale reveal is still refused,
    whether or not the sender ever called commit_turn."""
    inboxes = PeerInboxes()

    with pytest.raises(SimulationError, match="expired"):
        inboxes.accept_reveal(
            {"message_id": "mid-4", "commit": "c" * 64, "step": 1, "expires_at_epoch": 1.0}
        )
