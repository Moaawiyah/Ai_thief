"""Focused edge-case tests for the Thief runtime."""

import queue

import pytest

from tests.runtime_support import QueueTransport
from tests.test_runtime import config
from thief_agent.constants import Direction, MoveType
from thief_agent.domain.protocol import ProtocolError, TurnMessage
from thief_agent.peer.handshake import Negotiation, terms_from_config
from thief_agent.peer.runtime import ThiefRuntime
from thief_agent.strategy import Decision


def test_false_capture_claim_returns_honest_response(tmp_path):
    runtime = ThiefRuntime(config(tmp_path), QueueTransport(queue.Queue(), queue.Queue()))
    runtime._take_turn()
    message = TurnMessage(
        1, "police", "Where are you?", {}, "ab" * 32, "2026-01-01T00:00:00Z",
        capture_claim=[3, 3],
    )
    assert runtime._receive_turn(message.to_dict()) == {"claim": [3, 3], "caught": False}
    assert runtime._result is None


def test_barrier_on_current_cell_captures(tmp_path):
    runtime = ThiefRuntime(config(tmp_path), QueueTransport(queue.Queue(), queue.Queue()))
    runtime._take_turn()
    message = TurnMessage(
        1, "police", "Wall.", {}, "ab" * 32, "2026-01-01T00:00:00Z",
        barrier_placed=[4, 3],
    )
    assert runtime._receive_turn(message.to_dict()) is None
    assert runtime._result == "capture"


def test_invalid_police_turn_is_rejected(tmp_path):
    runtime = ThiefRuntime(config(tmp_path), QueueTransport(queue.Queue(), queue.Queue()))
    with pytest.raises(ProtocolError):
        runtime._receive_turn({"step": 1})


def test_replayed_police_turn_is_ignored_before_belief_fusion(tmp_path):
    runtime = ThiefRuntime(config(tmp_path), QueueTransport(queue.Queue(), queue.Queue()))
    runtime._take_turn()
    message = TurnMessage(
        1, "police", "Look north.", {"0,0": 0.9}, "ab" * 32, "2026-01-01T00:00:00Z"
    ).to_dict()

    runtime._receive_turn(message)
    matrix = runtime.belief.as_matrix()
    runtime._receive_turn(message)

    assert runtime._last_replayed is True
    assert runtime.belief.as_matrix() == matrix
    assert len(runtime.history) == 1
    assert "already-played" in runtime.disputes[-1]


def test_illegal_brain_action_falls_back_to_hold(tmp_path):
    class InvalidBrain:
        def decide(self, state, belief):
            return Decision(MoveType.MOVE, Direction.N)

    runtime = ThiefRuntime(
        config(tmp_path), QueueTransport(queue.Queue(), queue.Queue()), InvalidBrain()
    )
    runtime.state.position = (0, 0)
    runtime.state.visited = {(0, 0)}
    runtime._take_turn()
    assert runtime.state.step_number == 1
    assert runtime.state.position == (0, 0)


def test_silent_police_causes_timeout_and_failed_audit(tmp_path):
    cfg = config(tmp_path)

    class SilentTransport:
        def exchange_agreement(self, message):
            return Negotiation(terms_from_config(cfg), {"group_id": "police"}).signed()

        def send_turn(self, message):
            pass

        def poll_turn(self, timeout):
            return None

        def exchange_audit(self, payload):
            return None

    result = ThiefRuntime(cfg, SilentTransport()).run()
    assert result["result"] == "timeout"
    assert result["audit"]["passed"] is False
