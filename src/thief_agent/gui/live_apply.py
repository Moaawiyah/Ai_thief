"""Pure event-to-window mapping for the live heatmap."""


def apply_event(window, event: dict) -> None:
    kind = event["type"]
    if kind == "error":
        window.set_turn(False, "ERROR - see status")
        window.set_label("status", event["message"])
        return
    if "view" in event:
        window.render(event["view"])
    if kind == "negotiated":
        window.set_label("status", "Terms agreed and signature verified (SHA-256)")
        window.set_label("hint_in", f"opponent: {(event.get('peer') or {}).get('group_id', 'unknown')}")
        window.set_turn(True)
    elif kind == "incoming":
        window.set_label("hint_in", f"step {event['step']}: {event.get('hint') or '(silent)'}")
        window.set_turn(True)
    elif kind == "replay_ignored":
        window.set_label("status", f"replayed turn {event['step']} ignored (not answered)")
    elif kind == "moved":
        decision = event["decision"]
        window.set_label("hint_out", f"step {event['view']['step']}: {event.get('hint') or '(silent)'}")
        window.set_label("verdict", getattr(decision, "reasoning", "") or getattr(decision, "verdict", "-"))
        window.set_label("commit", f"{event['commit'][:32]}...")
        window.set_turn(False)
    elif kind == "game_over":
        summary = event["summary"]
        winner = summary.get("winner") or "nobody"
        window.set_turn(False, f"GAME OVER: {summary.get('result')} - winner {winner.upper()}")
        audit = summary.get("audit", {})
        outcome = "not exchanged" if audit.get("skipped") else f"{'PASSED' if audit.get('passed') else 'FAILED'}"
        window.set_label("status", f"Audit {outcome}, {audit.get('own', {}).get('verified_steps', 0)} steps")
