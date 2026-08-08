"""belief_log.record: one Bayes-filter snapshot per accepted turn, never per replay."""

from thief_agent.domain.belief import BeliefGrid
from thief_agent.peer import belief_log
from thief_agent.peer.turn_handler import IncomingOutcome


class FakeHandler:
    def __init__(self, history):
        self.history = history


class FakeRuntime:
    def __init__(self, history):
        self.handler = FakeHandler(history)
        self.belief = BeliefGrid(7)
        self.belief_log: list[dict] = []


def turn(step, smell_grid=None):
    return {"step": step, "hint": "", "smell_grid": smell_grid or {}}


def test_records_the_step_smell_grid_and_current_belief():
    runtime = FakeRuntime([turn(1, {"3,3": 0.9})])

    belief_log.record(runtime, IncomingOutcome())

    assert runtime.belief_log == [
        {"step": 1, "smell_grid": {"3,3": 0.9}, "belief": runtime.belief.as_matrix()}
    ]


def test_a_replayed_turn_is_never_logged():
    """A replay never reached diffuse()/observe_smell() -- logging it here
    would duplicate the prior real entry under a misleading new step."""
    runtime = FakeRuntime([turn(1)])

    belief_log.record(runtime, IncomingOutcome(replayed=True))

    assert runtime.belief_log == []


def test_an_empty_history_is_never_logged():
    """Defensive: nothing has been folded in yet, so there is nothing to snapshot."""
    runtime = FakeRuntime([])

    belief_log.record(runtime, IncomingOutcome())

    assert runtime.belief_log == []


def test_each_call_appends_rather_than_overwrites():
    runtime = FakeRuntime([turn(1)])
    belief_log.record(runtime, IncomingOutcome())
    runtime.handler.history.append(turn(2))

    belief_log.record(runtime, IncomingOutcome())

    assert [entry["step"] for entry in runtime.belief_log] == [1, 2]
