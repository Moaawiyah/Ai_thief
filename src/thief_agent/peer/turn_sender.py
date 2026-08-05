"""Outbound turn assembly for a ThiefRuntime: decide, seal, deposit scent, and
push the wire message. Split from runtime.py to keep it small.
"""

from thief_agent.domain.actions import hold
from thief_agent.domain.rules import SURVIVAL
from thief_agent.peer import runtime_control
from thief_agent.peer.sealing import build_turn_message
from thief_agent.peer.step_records import sealed_step_record

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

    decision = rt.brain.decide(rt.state, rt.belief)
    action = decision.action()
    if not rt.state.apply_move(action):
        action = hold()
        rt.state.apply_move(action)
    hint = rt.hint_writer(rt.state, None, rt._last_police_hint)

    prior_commit = rt.records[-1]["commit"] if rt.records else ""
    record = sealed_step_record(
        rt.state,
        decision,
        hint,
        {"model": "heuristic", "total": 0},
        0,
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
