"""Run a SERIES of N sub-games against the Police peer.

The transport (and thus this peer's MCP server) is built ONCE by the caller and
reused across sub-games — it is never torn down between them. Each sub-game gets
a fresh ThiefRuntime (fresh state/belief/scent/commit-chain). Thief always plays
thief (no role alternation — that's a Police-only concept since only Police ever
plays both sides across a series).
"""

from dataclasses import dataclass

from thief_agent.exceptions import RestartSeries
from thief_agent.peer.control_link import ControlLink
from thief_agent.peer.controls import GameControls
from thief_agent.peer.runtime import ThiefRuntime
from thief_agent.peer.sealing import identity_from_config

__all__ = ["SeriesResult", "run_series"]

MAX_RESTARTS = 10  # backstop so a restart storm can never loop forever


@dataclass
class SeriesResult:
    """Everything the emitters need after a whole series has been played."""

    summaries: list[dict]
    own_identity: dict
    peer_identity: dict
    game_id: str | None
    game_uid: str | None


def _play_all(config, brain, hint_writer, transport, listener, controls, link) -> SeriesResult:
    """One full pass over the sub-games (the whole series) with a shared ControlLink."""
    num_games = config.get("game.num_games", 1)
    own_identity = identity_from_config(config)
    summaries: list[dict] = []
    peer_identity: dict = {}
    game_id = game_uid = None
    for sub_game_number in range(1, num_games + 1):
        runtime = ThiefRuntime(
            config, transport, brain=brain, hint_writer=hint_writer,
            listener=listener, controls=controls, sub_game_number=sub_game_number,
            link=link,
        )
        summaries.append(runtime.run())
        peer_identity = runtime.peer_identity or peer_identity
        game_id, game_uid = runtime.game_id, runtime.game_uid
    return SeriesResult(summaries, own_identity, peer_identity, game_id, game_uid)


def run_series(config, transport, brain=None, hint_writer=None,
               listener=None, controls=None) -> SeriesResult:
    """Play the whole series; a control-channel RestartSeries restarts it from
    sub-game 1 (the ControlLink is shared so the enable state survives a restart)."""
    controls = controls or GameControls()
    link = ControlLink("thief", transport, controls, listener)
    attempt = 0
    while True:
        try:
            return _play_all(config, brain, hint_writer, transport, listener, controls, link)
        except RestartSeries:
            attempt += 1
            # Clear any stale turn/control messages from the aborted sub-game so the
            # restarted series never consumes them (both peers drain before the fresh
            # handshake, and no new turn arrives until after it).
            drain = getattr(transport, "drain_inboxes", None)
            if drain is not None:
                drain()
            if listener is not None:
                listener({"type": "series_restart", "attempt": attempt})
            if attempt > MAX_RESTARTS:
                raise
