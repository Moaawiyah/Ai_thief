"""The pre-game handshake step of a ThiefRuntime, split out to keep runtime.py
small: exchange signed terms + identity, verify, and derive the shared ids.

The `Negotiation` class lives at domain level (mirrors the Police peer) and
term/identity building + validation lives in `peer/sealing.py` — both
re-exported here so existing call sites keep working unchanged.
"""

import time

from thief_agent.domain.game_ids import derive_game_ids
from thief_agent.domain.negotiation import Negotiation
from thief_agent.peer.sealing import (
    identity_from_config,
    terms_from_config,
    validate_agreement,
    validate_config,
)

__all__ = [
    "Negotiation",
    "terms_from_config",
    "identity_from_config",
    "validate_agreement",
    "validate_config",
    "negotiate",
]


def negotiate(rt) -> None:
    """Run the mutual agreement + identity exchange for one sub-game.

    Sets rt.peer_identity, rt.game_id, rt.game_uid and (re)starts the game clock.
    """
    terms = terms_from_config(rt.config)
    negotiation = Negotiation(terms, identity_from_config(rt.config))
    peer_message = rt.transport.exchange_agreement(negotiation.signed())
    negotiation.verify_peer(peer_message)
    rt.peer_identity = negotiation.peer_identity
    rt.game_id, rt.game_uid = derive_game_ids(
        terms,
        identity_from_config(rt.config).get("group_id", "unknown-group"),
        rt.peer_identity.get("group_id", "unknown-group"),
    )
    rt.started_monotonic = time.monotonic()  # game clock starts at agreement
