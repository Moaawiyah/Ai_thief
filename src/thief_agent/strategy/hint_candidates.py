"""Grounded strategic claims that an LLM may turn into a short verbal hint.

Thief-only: always the "lure the Police away" scoring function.
"""

from dataclasses import dataclass

_ZONES = ("north", "south", "east", "west", "center")
_LANDMARKS = {
    "New York": {
        "north": "Harlem",
        "south": "Wall Street",
        "east": "East Village",
        "west": "West Side",
        "center": "Times Square",
    },
    "London": {
        "north": "Camden",
        "south": "the Thames",
        "east": "Tower Bridge",
        "west": "Soho",
        "center": "Big Ben",
    },
    "Paris": {
        "north": "Montmartre",
        "south": "Left Bank",
        "east": "Bastille",
        "west": "Arc de Triomphe",
        "center": "the Louvre",
    },
}
_DEFAULT = {
    "north": "north gate",
    "south": "harbor",
    "east": "east gate",
    "west": "west gate",
    "center": "old market",
}

__all__ = ["HintCandidate", "ranked_hint_candidates"]


@dataclass(frozen=True)
class HintCandidate:
    """One locally grounded location claim and its deterministic truth label."""

    action_id: str
    zone: str
    cue: str
    verdict: str
    utility: float
    fallback_message: str
    effect: str

    def prompt_value(self) -> dict:
        return {
            "action_id": self.action_id,
            "claimed_zone": self.zone,
            "required_phrase": self.cue,
            "verdict": self.verdict,
            "estimated_utility": round(self.utility, 3),
            "estimated_effect": self.effect,
            "safe_example": self.fallback_message,
        }


def _zone_of(cell, size: int) -> str:
    midpoint = (size - 1) / 2
    row_delta, col_delta = cell[0] - midpoint, cell[1] - midpoint
    if abs(row_delta) < 1 and abs(col_delta) < 1:
        return "center"
    if abs(row_delta) >= abs(col_delta):
        return "south" if row_delta > 0 else "north"
    return "east" if col_delta > 0 else "west"


def _zone_cell(zone: str, size: int) -> tuple[int, int]:
    edge, middle = size - 1, (size - 1) // 2
    return {
        "north": (0, middle),
        "south": (edge, middle),
        "east": (middle, edge),
        "west": (middle, 0),
        "center": (middle, middle),
    }[zone]


def _thief_score(state, belief, claim_cell, lying: bool) -> tuple[float, str]:
    lure_distance = state.board.distance(state.position, claim_cell)
    police_estimate = belief.most_likely()
    approach_cost = state.board.distance(police_estimate, claim_cell)
    score = 5.0 * lure_distance - 0.25 * approach_cost + 2.0 * lying
    effect = f"lure police {lure_distance} cells from true position"
    return score, effect


def ranked_hint_candidates(state, belief, setting: str) -> list[HintCandidate]:
    """Return five legal claims, best-first, with truth decided from private state."""
    landmarks = _LANDMARKS.get(setting, _DEFAULT)
    actual_zone = _zone_of(state.position, state.board.size)
    candidates = []
    for zone in _ZONES:
        cue = landmarks[zone]
        lying = zone != actual_zone
        claim_cell = _zone_cell(zone, state.board.size)
        utility, effect = _thief_score(state, belief, claim_cell, lying)
        message = f"Catch me near {cue} in the {zone}."
        candidates.append(
            HintCandidate("", zone, cue, "lie" if lying else "truth", utility, message, effect)
        )
    candidates.sort(key=lambda item: (-item.utility, item.zone))
    return [
        HintCandidate(
            f"H{index}",
            item.zone,
            item.cue,
            item.verdict,
            item.utility,
            item.fallback_message,
            item.effect,
        )
        for index, item in enumerate(candidates)
    ]
