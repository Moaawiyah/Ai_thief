"""Outbound turn assembly for a ThiefRuntime: decide, seal, deposit scent, and
push the wire message. Split from runtime.py to keep it small.
"""

from dataclasses import replace

from thief_agent.domain.actions import hold
from thief_agent.domain.rules import SURVIVAL
from thief_agent.peer import runtime_control
from thief_agent.peer.sealing import build_turn_message
from thief_agent.peer.step_records import sealed_step_record
from thief_agent.peer.token_meter import step_usage, total

__all__ = ["take_turn"]


def take_turn(rt, claim_response: dict | None = None) -> None:
    """Compute, seal, and send one of rt's turns, pumping the control channel
    around it (status broadcast + honoring pause/stop/quit/restart)."""
    runtime_control.pump(rt, runtime_control.THINKING)
    rt.controls.wait_if_paused()
    if rt.controls.stopped:
        rt._result = "technical_loss"
        return
    runtime_control.pump(rt, runtime_control.THINKING)
    runtime_control.check(rt)
    if rt._result is not None:
        return

    token_count_before = total(rt)
    decision = rt.brain.decide(rt.state, rt.belief)
    action = decision.action()
    if not rt.state.apply_move(action):
        action = hold()
        rt.state.apply_move(action)
    hint, decision = _write_hint(rt, decision)

    prior_commit = rt.records[-1]["commit"] if rt.records else ""
    usage, tokens_step = step_usage(rt, token_count_before)
    rt.tokens_total += tokens_step
    record = sealed_step_record(
        rt.state,
        decision,
        hint,
        usage,
        rt.tokens_total,
        game_id=rt.game_id or "",
        sub_game_number=rt.sub_game_number,
        prior_commit=prior_commit,
    )
    rt.records.append(record)
    win = rt.rules.survival_result(rt.state)
    message = build_turn_message(
        rt.state,
        hint,
        rt.scent.emit(rt.state.position),
        record,
        None,
        claim_response,
        {"type": "survival"} if win else None,
        response_timeout=rt.config.get("network.response_timeout_seconds", 30),
    )
    rt.transport.send_turn(message.to_dict())
    rt._notify({"type": "moved", "decision": decision, "commit": record["commit"], "hint": hint})
    if win:
        rt._result = SURVIVAL


def _write_hint(rt, decision):
    """Use grounded LLM hints when configured, retaining legacy writers."""
    writer = rt.hint_writer
    if not hasattr(writer, "say"):
        return writer(rt.state, None, rt._last_police_hint), decision
    deadline = rt.config.get("trash_talk.timeout_seconds") or rt.config.get(
        "llm.step_deadline_seconds"
    )
    hint, _, _, _ = writer.say(
        rt.state,
        rt.belief,
        rt.config.get("play.setting", ""),
        rt._last_police_hint,
        deadline,
    )
    return hint, replace(
        decision,
        hint_source=getattr(writer, "last_source", "template"),
        hint_fallback_reason=getattr(writer, "last_fallback_reason", ""),
    )
