"""Create the selected, gatekeeper-wrapped LLM provider."""

from thief_agent.exceptions import ConfigError
from thief_agent.sdk.providers import GatedLlm, StubLlm
from thief_agent.shared.gatekeeper import ApiGatekeeper


def build_llm(config, stub: bool = False):
    """Build the configured tactics provider, or the deterministic stub."""
    provider_name = str(config.get("llm.provider") or "template").lower()
    if stub or provider_name == "template":
        return StubLlm()
    if provider_name == "ollama":
        from thief_agent.infra.ollama_provider import OllamaLlmProvider

        return GatedLlm(OllamaLlmProvider(config), ApiGatekeeper(config, "ollama"))
    if provider_name not in {"claude", "claude_cli"}:
        raise ConfigError("llm.provider must be template, ollama, or claude_cli")
    from thief_agent.infra.llm_provider import ClaudeCliProvider

    return GatedLlm(ClaudeCliProvider(config), ApiGatekeeper(config, "claude"))


__all__ = ["build_llm"]
