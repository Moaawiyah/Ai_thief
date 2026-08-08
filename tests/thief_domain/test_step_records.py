"""The terminal notification must not collide with the last turn's commit.

A real opponent's replay guard is keyed on `commit`: two messages that share
one are indistinguishable from a duplicate, and the second is silently
dropped. `build_terminal_message` used to reuse the prior record's commit
verbatim -- this is the regression test for that bug (a real match: the
Thief believed it was captured and stopped, while the Police window sat
forever at "replayed turn N ignored", because its capture confirmation never
arrived as anything but an apparent repeat of the turn already played).
"""

from thief_agent.peer.step_records import build_terminal_message


def _sealed_record(step: int = 3) -> dict:
    payload = {"step": step, "role": "thief"}
    return {"payload": payload, "nonce": "aa" * 16, "commit": "bb" * 32}


def test_the_terminal_commit_is_not_the_reused_prior_commit():
    record = _sealed_record()

    message = build_terminal_message(record, record["payload"]["step"], {"caught": True})

    assert message.commit != record["commit"]


def test_two_terminal_messages_never_share_a_commit():
    """Even sealing the same step/claim twice must not collide -- the nonce,
    not the content, is what keeps the fingerprint fresh."""
    record = _sealed_record()

    first = build_terminal_message(record, 3, {"caught": True})
    second = build_terminal_message(record, 3, {"caught": True})

    assert first.commit != second.commit


def test_the_terminal_message_still_carries_the_capture_confirmation():
    record = _sealed_record()

    message = build_terminal_message(record, 3, {"claim": [4, 3], "caught": True})

    assert message.claim_response == {"claim": [4, 3], "caught": True}
    assert message.sender == "thief"
