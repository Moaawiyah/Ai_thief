"""Thief peer entrypoint and repository identity."""

import argparse
import json
from pathlib import Path

PEER_ROLE = "thief"


def main(argv: list[str] | None = None) -> None:
    """Run a mailbox or one configured Thief game."""
    parser = argparse.ArgumentParser(description="Run the Thief peer")
    commands = parser.add_subparsers(dest="command", required=True)
    server = commands.add_parser("server", help="start only the FastMCP mailbox")
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8802)
    play = commands.add_parser("play", help="run one configured game")
    play.add_argument("--config-dir", default="config/thief")
    play.add_argument("--host")
    play.add_argument("--port", type=int)
    play.add_argument("--opponent-url")
    gui = commands.add_parser("gui", help="run a live game with a heatmap window")
    gui.add_argument("--config-dir", default="config/thief")
    gui.add_argument("--host")
    gui.add_argument("--port", type=int)
    gui.add_argument("--opponent-url")
    replay = commands.add_parser("replay", help="replay a saved Thief match")
    replay.add_argument("log", help="saved match JSON")
    replay.add_argument("--config-dir", default="config/thief")
    replay.add_argument("--opponent-log")
    args = parser.parse_args(argv)

    if args.command == "server":
        from thief_agent.infra.mcp_server import PeerInboxes, build_peer_server

        build_peer_server(PEER_ROLE, PeerInboxes()).run(
            transport="http", host=args.host, port=args.port,
            show_banner=False, log_level="warning",
        )
        return

    from thief_agent.shared.config import ConfigError, ConfigManager

    try:
        config = ConfigManager(args.config_dir)
    except ConfigError as exc:
        parser.error(str(exc))
    if getattr(args, "host", None):
        config.override("network.host", args.host)
    if getattr(args, "port", None):
        config.override("network.my_port", args.port)
    if getattr(args, "opponent_url", None):
        config.override("network.opponent_url", args.opponent_url)
    if args.command == "play":
        from thief_agent.peer.runtime import ThiefRuntime

        print(json.dumps(ThiefRuntime(config).run(), indent=2))
        return
    if args.command == "gui":
        from thief_agent.gui.player import LivePeerApp
        from thief_agent.sdk import MatchOptions, ThiefAgentSDK

        LivePeerApp(ThiefAgentSDK(MatchOptions(config_dir=args.config_dir), config=config)).run()
        return
    from thief_agent.gui.replay import ReplayApp

    try:
        log = json.loads(Path(args.log).read_text(encoding="utf-8"))
        opponent = (
            json.loads(Path(args.opponent_log).read_text(encoding="utf-8"))
            if args.opponent_log
            else None
        )
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"could not read replay log: {exc}")
    ReplayApp(config, log, opponent).run()
