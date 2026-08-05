"""Build and rank the only actions an LLM tactics controller may select.

Thief-only: there is no BARRIER candidate (the Thief never places one) and no
police-chase utility function — only the evasion objective.
"""

from dataclasses import dataclass, replace

from thief_agent.constants import Direction, MoveType

__all__ = ["ActionCandidate", "ranked_candidates"]


@dataclass(frozen=True)
class ActionCandidate:
    """One legality-checked action with deterministic tactical evidence."""

    action_id: str
    move_type: MoveType
    direction: Direction | None
    target: tuple[int, int]
    utility: float
    rationale: str

    def prompt_value(self) -> dict:
        """Return a compact, JSON-safe model view without hidden state."""
        return {
            "action_id": self.action_id,
            "action": self.move_type.value,
            "direction": self.direction.value if self.direction else None,
            "target": list(self.target),
            "utility": round(self.utility, 3),
            "evidence": self.rationale,
        }


def _probability(belief, cell) -> float:
    return float(belief.as_matrix()[cell[0]][cell[1]])


def _reachable_area(board, start, barriers) -> int:
    seen = {start}
    pending = [start]
    while pending:
        cell = pending.pop(0)
        for neighbor in board.neighbors(cell, barriers):
            if neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    return len(seen)


def _thief_candidate(state, belief, direction, target) -> ActionCandidate:
    threat = belief.most_likely()
    distance = state.board.distance(target, threat)
    probability = _probability(belief, target)
    area = _reachable_area(state.board, target, state.barriers)
    novelty = int(target not in state.visited)
    utility = 4.0 * distance + 0.15 * area + 1.5 * novelty - 20.0 * probability
    rationale = (
        f"threat_distance={distance}; belief_risk={probability:.3f}; "
        f"reachable_area={area}; unvisited={bool(novelty)}"
    )
    return ActionCandidate("", MoveType.MOVE, direction, target, utility, rationale)


def ranked_candidates(state, belief) -> list[ActionCandidate]:
    """Return deterministic best-first candidates derived only from local knowledge."""
    moves = state.board.legal_moves(state.position, state.barriers)
    candidates = [_thief_candidate(state, belief, direction, target) for direction, target in moves]
    if not candidates:
        candidates.append(
            ActionCandidate("", MoveType.HOLD, None, state.position, 0.0, "no legal step")
        )
    candidates.sort(
        key=lambda item: (
            -item.utility,
            item.move_type.value,
            item.direction.value if item.direction else "",
        )
    )
    return [replace(item, action_id=f"A{index}") for index, item in enumerate(candidates)]
