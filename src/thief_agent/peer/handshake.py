"""Reference-compatible signed agreement exchange."""

import secrets

from thief_agent.domain.crypto import CommitReveal, CryptoError


class Negotiation:
    """Create and verify the shared terms exchanged before play."""

    def __init__(self, terms: dict, identity: dict | None = None):
        if not isinstance(terms, dict):
            raise TypeError("agreement terms must be an object")
        self.terms = terms
        self.identity = identity or {}
        self._nonce = secrets.token_hex(16)
        self.peer_identity: dict = {}

    def signed(self) -> dict:
        return {
            "terms": self.terms,
            "nonce": self._nonce,
            "signature": CommitReveal.commit_of(self.terms, self._nonce),
            "identity": self.identity,
        }

    def verify_peer(self, message: dict) -> None:
        if not isinstance(message, dict):
            raise CryptoError("agreement must be an object")
        if message.get("terms") != self.terms:
            raise CryptoError("agreement terms mismatch")
        try:
            CommitReveal.verify(message["terms"], message["nonce"], message["signature"])
        except KeyError as exc:
            raise CryptoError(f"agreement missing field: {exc.args[0]}") from exc
        self.peer_identity = message.get("identity", {})


def terms_from_config(config) -> dict:
    """Build the exact shared term map used by both peers."""
    return {
        "board_size": config.get("board.size"),
        "smell_grid_size": config.get("smell.grid_size", 5),
        "decay_per_step": config.get("smell.decay_per_step", 0.1),
        "emit_intensity": config.get("smell.emit_intensity", 0.9),
        "min_center_intensity": config.get("smell.min_center_intensity", 0.5),
        "max_steps": config.get("rules.max_steps"),
        "barriers_max": config.get("rules.barriers_max"),
        "setting": config.get("play.setting", ""),
        "hint_max_words": config.get("play.hint_max_words", 15),
        "axis_origin_corner": config.get("board.axis_origin_corner", "top-left"),
        "axis_start_index": config.get("board.axis_start_index", 0),
        "thief_start": config.get("positions.thief_start"),
        "cop_start": config.get("positions.cop_start"),
        "num_games": config.get("game.num_games", 1),
    }


def identity_from_config(config) -> dict:
    return {
        "group_id": config.get("game.group_id", "unknown-group"),
        "group_name": config.get("game.group_name", "unnamed"),
        "members": config.get("game.members", []),
        "repos": config.get("game.repos", {}),
        "mcp_servers": config.get("game.mcp_servers", {}),
    }


def validate_config(config) -> None:
    required = {
        "board.size": config.get("board.size"),
        "rules.max_steps": config.get("rules.max_steps"),
        "rules.survival_threshold": config.get("rules.survival_threshold"),
        "positions.thief_start": config.get("positions.thief_start"),
        "positions.cop_start": config.get("positions.cop_start"),
        "network.opponent_url": config.get("network.opponent_url"),
        "network.my_port": config.get("network.my_port"),
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError("Missing required configuration: " + ", ".join(missing))
