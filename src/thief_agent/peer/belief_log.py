"""One Bayes-filter update per accepted incoming turn, for a faithful replay
and for diagnosing the filter itself -- not just its eventual effect on
where Thief walked. Split out of `runtime.py` to keep it within the
project's 150-line rule.
"""

from thief_agent.peer.turn_handler import IncomingOutcome


def record(runtime, outcome: IncomingOutcome) -> None:
    """Append the belief snapshot behind an accepted, non-replayed turn.

    A replayed message never reached `belief.diffuse()`/`observe_smell()`
    (see `TurnHandler.process`), so logging one here would duplicate the
    prior real entry under a misleading new step.
    """
    if outcome.replayed or not runtime.handler.history:
        return
    last = runtime.handler.history[-1]
    runtime.belief_log.append(
        {
            "step": last["step"],
            "smell_grid": last["smell_grid"],
            "belief": runtime.belief.as_matrix(),
        }
    )
