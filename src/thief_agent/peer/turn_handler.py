"""TurnHandler: apply the Police's TurnMessage to MY local view.

The only knowledge this peer ever gains about the Police flows through here:
NL hint, smell grid, declared barriers, claims. There is no shared board to
consult, so replay/duplicate and step-ordering checks live here too — a
Thief-specific hardening Police's own handler does not need.

Malformed or out-of-order messages raise `ProtocolError` (the runtime treats
that as a technical loss); everything else is reported through
`IncomingOutcome` so the runtime can decide what happens next.
"""

from dataclasses import dataclass

from thief_agent.domain.belief import BeliefGrid
from thief_agent.domain.own_state import OwnGameState
from thief_agent.domain.protocol import ProtocolError, TurnMessage
from thief_agent.domain.rules import CAPTURE, SURVIVAL, GameRules
from thief_agent.language import infer_likelihoods

__all__ = ["IncomingOutcome", "TurnHandler"]


@dataclass
class IncomingOutcome:
    """Flags raised by one incoming, well-formed Police message."""

    result: str | None = None  # CAPTURE / SURVIVAL, if decided
    claim_response: dict | None = None  # honest answer to attach to my next message
    replayed: bool = False  # a duplicate of an already-played turn


class TurnHandler:
    """Folds Police messages into belief/scent/barrier knowledge."""

    def __init__(self, state: OwnGameState, belief: BeliefGrid, rules: GameRules):
        self.state = state
        self.belief = belief
        self.rules = rules
        self.history: list[dict] = []  # every received message, for GUI/replay
        self.disputes: list[str] = []
        self.incoming_step = 0
        self._seen_turns: set[str] = set()

    def process(self, raw: dict) -> IncomingOutcome:
        """Raise ProtocolError for a malformed or out-of-order message."""
        message = TurnMessage.from_dict(raw)
        fingerprint = message.commit or f"step-{message.step}"
        if fingerprint in self._seen_turns:
            self.disputes.append(
                f"ignored a repeat of an already-played turn (step {message.step})"
            )
            return IncomingOutcome(replayed=True)
        if message.sender != "police" or message.step != self.incoming_step + 1:
            raise ProtocolError("unexpected Police turn sender or step")
        self._seen_turns.add(fingerprint)
        self.incoming_step = message.step
        self.history.append(message.to_dict())

        # The Police has completed one turn: predict its legal movement, then
        # sharpen the prediction with the fresh scent and any verbal location cue.
        # Known barriers are impassable, so the prediction must not spread mass
        # onto them (they were leaking probability the filter never got back).
        self.belief.diffuse(self.state.barriers)
        self.belief.observe_smell(message.smell_grid)
        self.belief.observe_likelihoods(infer_likelihoods(message.hint, self.state.board.size))

        outcome = IncomingOutcome()
        if message.barrier_placed:
            barrier = tuple(message.barrier_placed)
            if not self.state.board.in_bounds(barrier):
                raise ProtocolError("Police barrier is off the board")
            self.state.note_barrier(barrier)
            self.belief.exclude(barrier)
            if self.rules.barrier_captures(self.state, barrier) or self.rules.confinement_capture(
                self.state
            ):
                return IncomingOutcome(result=CAPTURE)
        if message.win_claim:
            return IncomingOutcome(result=SURVIVAL)
        if message.capture_claim:
            claim = tuple(message.capture_claim)
            caught = self.rules.is_captured(self.state, claim)
            outcome.claim_response = {"claim": list(claim), "caught": caught}
            if caught:
                outcome.result = CAPTURE
        if outcome.result != CAPTURE:
            self.belief.exclude(self.state.position)
        return outcome
