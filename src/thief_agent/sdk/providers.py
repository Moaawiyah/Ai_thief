"""Provider adapters used by the public SDK composition root."""


class StubLlm:
    """Unparseable deterministic provider that forces the Python fallback."""

    last_usage = {"model": "stub", "in": 0, "out": 0, "total": 0}
    tokens_consumed = 0

    def send(self, prompt: str, timeout=None, schema=None) -> str:
        del prompt, timeout, schema
        return "stub reply - no structured move here"


class GatedLlm:
    """Expose a provider through the shared API gatekeeper."""

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
        return self._gatekeeper.execute(self._provider.send, prompt, timeout=timeout, schema=schema)


__all__ = ["GatedLlm", "StubLlm"]
