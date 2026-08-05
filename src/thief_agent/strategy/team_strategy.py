"""An example custom Thief brain demonstrating the `_pick_move` extension seam.

Selectable via `[strategy] thief_class = "thief_agent.strategy.team_strategy:MobilityThiefBrain"`
in game.toml (see strategy/__init__.py:resolve_brain). The shipped default
brain is still `domain.brains.ThiefBrain`.
"""

from thief_agent.domain.brains import ThiefBrain

__all__ = ["MobilityThiefBrain"]


def _reachable_area(board, start, barriers) -> int:
    """Count cells reachable from ``start`` under current barriers."""
    seen = {start}
    pending = [start]
    while pending:
        cell = pending.pop(0)
        for neighbor in board.neighbors(cell, barriers):
            if neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    return len(seen)


def _probability(belief, cell) -> float:
    """Read one cell from the public belief matrix."""
    return belief.as_matrix()[cell[0]][cell[1]]


class MobilityThiefBrain(ThiefBrain):
    """Evade belief peaks while preserving future mobility and unseen routes."""

    def _pick_move(self, moves, state, belief):
        threat = belief.most_likely()

        def score(item):
            _, target = item
            return (
                state.board.distance(target, threat),
                -_probability(belief, target),
                _reachable_area(state.board, target, state.barriers),
                target not in state.visited,
                -target[0],
                -target[1],
            )

        return max(moves, key=score)
