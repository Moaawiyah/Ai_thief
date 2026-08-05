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
from thief_agent.shared.config import ConfigManager

DEFAULT_CONNECT_TIMEOUT = 60.0
DEFAULT_REPLY_TIMEOUT = 30.0


class StubLlm:
    """Unparseable on purpose: forces the deterministic fallback policy."""

    last_usage = {"model": "stub", "in": 0, "out": 0, "total": 0}
    tokens_consumed = 0

    def send(self, prompt: str, timeout=None, schema=None) -> str:
        return "stub reply - no structured move here"


class GatedLlm:
    """A structured LLM provider routed through the API gatekeeper."""

    def __init__(self, provider, gatekeeper):
        self._provider = provider
        self._gatekeeper = gatekeeper

    @property
    def last_usage(self) -> dict:
        return self._provider.last_usage

    @property
    def tokens_consumed(self) -> int:
        return self._provider.tokens_consumed

    def send(self, prompt: str, timeout=None, schema=None) -> str:
        return self._gatekeeper.execute(
            self._provider.send, prompt, timeout=timeout, schema=schema
        )


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
            self._transport = McpTransport(self.opponent_url, inboxes, **self.transport_timeouts())
        return self._transport

    def transport_timeouts(self) -> dict[str, float]:
        """Resolve transport deadlines from private/shared config with safe fallbacks."""
        return {
            "connect_timeout": float(
                self.config.get("network.watchdog_timeout_seconds") or DEFAULT_CONNECT_TIMEOUT
            ),
            "reply_timeout": float(
                self.config.get("network.response_timeout_seconds") or DEFAULT_REPLY_TIMEOUT
            ),
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

    def _build_llm(self, stub: bool = False):
        """Resolve the movement-tactics LLM (independent of the hint-writer's own
        provider): template/stub by default, or a gatekeeper-wrapped provider."""
        provider_name = str(self.config.get("llm.provider", "template")).lower()
        if stub or provider_name == "template":
            return StubLlm()
        from thief_agent.shared.gatekeeper import ApiGatekeeper

        if provider_name == "ollama":
            from thief_agent.infra.ollama_provider import OllamaLlmProvider

            return GatedLlm(OllamaLlmProvider(self.config), ApiGatekeeper(self.config, "ollama"))
        if provider_name not in {"claude", "claude_cli"}:
            raise ConfigError("llm.provider must be template, ollama, or claude_cli")
        from thief_agent.infra.llm_provider import ClaudeCliProvider

        return GatedLlm(ClaudeCliProvider(self.config), ApiGatekeeper(self.config, "claude"))

    def play_series(self, stub_llm: bool = False):
        """Play the whole configured series (game.num_games sub-games), sharing
        this SDK's transport/controls across them. Returns a `SeriesResult`."""
        from thief_agent.peer.sealing import validate_agreement
        from thief_agent.sdk.series import run_series

        validate_agreement(self.config)
        self._llm = self._build_llm(stub_llm)
        return run_series(
            self.config, self.connect(), brain=self._brain,
            listener=self.listener, controls=self.controls or GameControls(),
        )

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
