"""The public Thief SDK composition root.

The SDK is the only layer a front end needs: it resolves configuration, lazily
opens the mailbox, builds one runtime, plays it, and persists its full summary.
Transport injection keeps the same API usable with queue-based test doubles and
replay tooling without opening a socket.
"""

import json
from pathlib import Path

from thief_agent.exceptions import ConfigError
from thief_agent.infra.mcp_client import McpTransport
from thief_agent.infra.mcp_server import start_peer_server
from thief_agent.peer.controls import GameControls
from thief_agent.peer.runtime import ThiefRuntime
from thief_agent.sdk.options import MatchOptions
from thief_agent.sdk.provider_factory import build_llm
from thief_agent.shared.config import ConfigManager


class ThiefAgentSDK:
    """Configure, connect, and play one Thief sub-game."""

    def __init__(
        self,
        options=None,
        *,
        config=None,
        transport=None,
        brain=None,
        listener=None,
        controls=None,
        workdir: str | Path = ".",
    ) -> None:
        self.options = options or MatchOptions()
        self.config = config if config is not None else ConfigManager(self.options.config_dir)
        if self.options.port is not None:
            self.config.override("network.my_port", self.options.port)
        if self.options.opponent_url is not None:
            self.config.override("network.opponent_url", self.options.opponent_url)
        self._transport = transport
        self._runtime: ThiefRuntime | None = None
        self._brain = brain
        self.listener = listener
        self.controls = controls
        self._workdir = Path(workdir)

    @property
    def host(self) -> str:
        return self.options.host

    @property
    def port(self) -> int:
        return int(self.options.port or self.config.require("network.my_port"))

    @property
    def opponent_url(self) -> str:
        return str(self.options.opponent_url or self.config.require("network.opponent_url"))

    def connect(self):
        """Open the Thief mailbox and outbound transport once."""
        if self._transport is None:
            inboxes = start_peer_server("thief", self.host, self.port)
            from thief_agent.shared.gatekeeper import ApiGatekeeper

            gatekeeper = ApiGatekeeper(self.config, "mcp")
            self._transport = McpTransport(
                self.opponent_url,
                inboxes,
                gatekeeper=gatekeeper,
                **self.transport_timeouts(),
            )
        return self._transport

    def transport_timeouts(self) -> dict[str, float]:
        """Resolve transport deadlines from private/shared config with safe fallbacks."""
        return {
            "connect_timeout": float(self.config.require("network.watchdog_timeout_seconds")),
            "reply_timeout": float(self.config.require("network.response_timeout_seconds")),
        }

    @property
    def runtime(self) -> ThiefRuntime:
        """Build the match runtime lazily and return the same instance thereafter."""
        if self._runtime is None:
            self._runtime = ThiefRuntime(
                self.config,
                self.connect(),
                brain=self._brain,
                listener=self.listener,
                controls=self.controls or GameControls(),
            )
        return self._runtime

    def play(self) -> dict:
        """Play one configured sub-game and return the complete summary."""
        return self.runtime.run()

    def restart(self) -> None:
        """Drop the finished/abandoned runtime so the next play() builds a
        fresh one. Same transport and port, reused -- rebinding it would race
        the port the old one still holds."""
        self._runtime = None

    def _build_llm(self, stub: bool = False):
        """Resolve the movement-tactics provider through the shared factory."""
        return build_llm(self.config, stub)

    def play_series(self, stub_llm: bool = False) -> dict:
        """Play the configured series and emit its audit/report artifacts."""
        from thief_agent.sdk.series_runner import play_series

        return play_series(self, stub_llm)

    def _save_log(self, summary: dict, report: dict) -> Path:
        logs_dir = self._workdir / self.config.get("paths.logs_dir", "logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        pattern = self.config.get("paths.log_filename", "{role}_match.json")
        path = logs_dir / pattern.format(role="thief")
        path.write_text(
            json.dumps({"summary": summary, "report": report}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def save_summary(self, summary: dict, path: str | Path) -> Path:
        """Persist the complete match record for reporting or replay."""
        destination = Path(path)
        destination.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return destination

    def load_summary(self, path: str | Path) -> dict:
        """Load a saved match record with user-facing configuration errors."""
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigError(f"Match log not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Match log is not valid JSON: {path}: {exc}") from exc


ThiefSDK = ThiefAgentSDK
