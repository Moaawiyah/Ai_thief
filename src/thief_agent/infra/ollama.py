"""Small, failure-tolerant client for a local Ollama dialogue model."""

import json
import urllib.error
import urllib.request

from thief_agent.exceptions import ProviderError

DEFAULT_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen3:4b"
_MAX_TOKENS = 96


class OllamaError(ProviderError):
    """Raised when Ollama cannot return usable text."""


class OllamaAsker:
    """Callable Ollama client that retains the provider's token counters."""

    def __init__(self, model: str, url: str, timeout: float):
        self.model, self.url, self.timeout = model, url, timeout
        self.last_usage = {"model": model, "in": 0, "out": 0, "total": 0}
        self.tokens_consumed = 0

    def __call__(self, prompt: str, system: str = "") -> str:
        wrapper = _request_ollama(prompt, system, self.model, self.url, self.timeout)
        tokens_in = int(wrapper.get("prompt_eval_count", 0) or 0)
        tokens_out = int(wrapper.get("eval_count", 0) or 0)
        total = tokens_in + tokens_out
        self.last_usage = {
            "model": self.model,
            "in": tokens_in,
            "out": tokens_out,
            "total": total,
        }
        self.tokens_consumed += total
        reply = wrapper.get("response")
        if not isinstance(reply, str):
            raise OllamaError(f"Ollama returned no text for {self.model}: {wrapper!r}")
        return reply


def _request_ollama(prompt: str, system: str, model: str, url: str, timeout: float) -> dict:
    """Perform the HTTP request and return the decoded provider envelope."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {"num_predict": _MAX_TOKENS},
    }
    if system:
        payload["system"] = system
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise OllamaError(f"Ollama call to {model} failed: {exc}") from exc


def ask_ollama(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    url: str = DEFAULT_URL,
    timeout: float = 5.0,
) -> str:
    """Request one non-streaming completion from Ollama."""
    return OllamaAsker(model, url, timeout)(prompt, system)


def ollama_asker(
    model: str = DEFAULT_MODEL,
    url: str = DEFAULT_URL,
    timeout: float = 5.0,
):
    """Return an injectable ``ask(prompt, system)`` function."""

    return OllamaAsker(model, url, timeout)
