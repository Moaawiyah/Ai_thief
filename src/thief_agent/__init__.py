"""Thief peer entrypoint and repository identity."""

import argparse

PEER_ROLE = "thief"


def main(argv: list[str] | None = None) -> None:
    """Run the Thief FastMCP mailbox until interrupted."""
    parser = argparse.ArgumentParser(description="Run the Thief FastMCP peer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8802)
    args = parser.parse_args(argv)

    from thief_agent.infra.mcp_server import PeerInboxes, build_peer_server

    server = build_peer_server(PEER_ROLE, PeerInboxes())
    server.run(
        transport="http",
        host=args.host,
        port=args.port,
        show_banner=False,
        log_level="warning",
    )
