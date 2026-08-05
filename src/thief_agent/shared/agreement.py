"""Validation for mandatory shared rules from the assignment's Appendix F."""

from thief_agent.exceptions import ConfigError

_FIXED_SCORING = {
    "capture_cop": 20,
    "capture_thief": 5,
    "survival_cop": 5,
    "survival_thief": 10,
    "tie_score": 2,
    "technical_loss": 0,
}
_FIXED_PHEROMONES = {
    "pheromone_center_intensity": 0.9,
    "pheromone_decay": 0.10,
    "pheromone_grid_size": 5,
}

__all__ = ["validate_shared_config"]


def _require(condition: bool, message: str) -> None:
    """Raise a configuration error when one binding rule is violated."""
    if not condition:
        raise ConfigError(message)


def validate_shared_config(shared: dict) -> None:
    """Validate fixed values and minimum bounds before opening a network port."""
    board = shared.get("board_and_agents", {})
    movement = shared.get("movement_and_barriers", {})
    league = shared.get("network_and_league", {})
    gate = shared.get("rate_limiter_gatekeeper", {})
    _require(board.get("grid_size", 0) >= 7, "grid_size must be at least 7")
    _require(board.get("num_agents") == 2, "num_agents must equal 2")
    _require(
        movement.get("move_set") == ["N", "S", "E", "W", "STAY"],
        "move_set must be N/S/E/W/STAY with no diagonals",
    )
    _require(movement.get("max_barriers", 0) >= 14, "max_barriers must be at least 14")
    _require(movement.get("max_moves", 0) >= 35, "max_moves must be at least 35")
    _require(
        movement.get("survival_threshold", 0) >= 35,
        "survival_threshold must be at least 35",
    )
    for key, expected_score in _FIXED_SCORING.items():
        _require(
            shared.get("scoring", {}).get(key) == expected_score,
            f"scoring.{key} must equal {expected_score}",
        )
    for key, expected_pheromone in _FIXED_PHEROMONES.items():
        _require(
            shared.get("pheromones", {}).get(key) == expected_pheromone,
            f"pheromones.{key} must equal {expected_pheromone}",
        )
    _require(
        league.get("num_games") in range(1, 7),
        "num_games must be 1-6; only 6 qualifies as a counted series",
    )
    _require(league.get("diversity_reward") == 10, "diversity_reward must equal 10")
    _require(league.get("min_games_to_pass", 0) >= 2, "min_games_to_pass must be at least 2")
    _require(league.get("max_games_per_team") == 10, "max_games_per_team must equal 10")
    _require(gate.get("requests_per_minute", 0) >= 30, "requests_per_minute must be at least 30")
    _require(gate.get("concurrent_requests", 0) >= 2, "concurrent_requests must be at least 2")
    _require(gate.get("retry_backoff_sec", 0) >= 5, "retry_backoff_sec must be at least 5")
    _require(gate.get("max_retries", 0) >= 3, "max_retries must be at least 3")
    _require(gate.get("queue_depth", 0) >= 100, "queue_depth must be at least 100")
    strategy = shared.get("strategy_agreement", {})
    if strategy.get("llm_tactics_allowed", False):
        _require(
            strategy.get("contract_version") == "1.0",
            "LLM tactics contract_version must equal 1.0",
        )
