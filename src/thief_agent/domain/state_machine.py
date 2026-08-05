"""Explicit match and turn state machines for the peer orchestrator."""

from enum import StrEnum

from thief_agent.exceptions import ProtocolStateError

__all__ = ["MatchState", "TurnState", "ProtocolStateMachine"]


class MatchState(StrEnum):
    """Whole-series lifecycle states."""

    BOOTSTRAP = "BOOTSTRAP"
    NEGOTIATING = "NEGOTIATING"
    STEP_ZERO = "STEP_ZERO"
    RUNNING_SUBGAME = "RUNNING_SUBGAME"
    FINAL_AUDIT = "FINAL_AUDIT"
    AGREEING_RESULT = "AGREEING_RESULT"
    REPORTING = "REPORTING"
    FINISHED = "FINISHED"
    ABORTED = "ABORTED"


class TurnState(StrEnum):
    """Per-turn commit, acknowledgement, reveal, and verification states."""

    WAITING_FOR_OPPONENT = "WAITING_FOR_OPPONENT"
    COMPUTING_MOVE = "COMPUTING_MOVE"
    COMMITTING = "COMMITTING"
    AWAITING_REVEAL = "AWAITING_REVEAL"
    VERIFYING = "VERIFYING"
    TECHNICAL_LOSS = "TECHNICAL_LOSS"


_MATCH_NEXT = {
    MatchState.BOOTSTRAP: {MatchState.NEGOTIATING, MatchState.STEP_ZERO, MatchState.ABORTED},
    MatchState.NEGOTIATING: {MatchState.STEP_ZERO, MatchState.ABORTED},
    MatchState.STEP_ZERO: {MatchState.RUNNING_SUBGAME, MatchState.ABORTED},
    MatchState.RUNNING_SUBGAME: {MatchState.FINAL_AUDIT, MatchState.ABORTED},
    MatchState.FINAL_AUDIT: {MatchState.AGREEING_RESULT, MatchState.ABORTED},
    MatchState.AGREEING_RESULT: {MatchState.REPORTING, MatchState.ABORTED},
    MatchState.REPORTING: {MatchState.FINISHED, MatchState.ABORTED},
}


class ProtocolStateMachine:
    """Reject illegal transitions and retain a machine-readable transition trace."""

    def __init__(self):
        self.match = MatchState.BOOTSTRAP
        self.turn = TurnState.WAITING_FOR_OPPONENT
        self.history = [{"scope": "match", "state": self.match.value}]

    def transition_match(self, target: MatchState) -> None:
        """Move to one legal match state."""
        if target not in _MATCH_NEXT.get(self.match, set()):
            raise ProtocolStateError(f"illegal match transition {self.match} -> {target}")
        self.match = target
        self.history.append({"scope": "match", "state": target.value})

    def local_turn(self) -> None:
        """Record the complete local commit-ack-reveal sequence."""
        for state in (
            TurnState.COMPUTING_MOVE,
            TurnState.COMMITTING,
            TurnState.AWAITING_REVEAL,
            TurnState.VERIFYING,
            TurnState.WAITING_FOR_OPPONENT,
        ):
            self.turn = state
            self.history.append({"scope": "turn", "state": state.value})

    def verified_incoming(self) -> None:
        """Record validation of an incoming reveal."""
        self.turn = TurnState.VERIFYING
        self.history.append({"scope": "turn", "state": self.turn.value})

    def technical_loss(self) -> None:
        """Enter the terminal turn failure state."""
        self.turn = TurnState.TECHNICAL_LOSS
        self.history.append({"scope": "turn", "state": self.turn.value})
