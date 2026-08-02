"""Thief peer entrypoint and repository identity."""

import argparse
import json

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
    args = parser.parse_args(argv)

    if args.command == "server":
        from thief_agent.infra.mcp_server import PeerInboxes, build_peer_server

        build_peer_server(PEER_ROLE, PeerInboxes()).run(
            transport="http", host=args.host, port=args.port,
            show_banner=False, log_level="warning",
        )
        return

    from thief_agent.peer.runtime import ThiefRuntime
    from thief_agent.shared.config import ConfigError, ConfigManager

    try:
        config = ConfigManager(args.config_dir)
    except ConfigError as exc:
        parser.error(str(exc))
    if args.host:
        config.override("network.host", args.host)
    if args.port:
        config.override("network.my_port", args.port)
    if args.opponent_url:
        config.override("network.opponent_url", args.opponent_url)
    print(json.dumps(ThiefRuntime(config).run(), indent=2))
