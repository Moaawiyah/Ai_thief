"""Small, failure-tolerant client for a local Ollama dialogue model."""

import json
import urllib.error
import urllib.request

DEFAULT_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen3:4b"
_MAX_TOKENS = 96


class OllamaError(RuntimeError):
    """Raised when Ollama cannot return usable text."""


def ask_ollama(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    url: str = DEFAULT_URL,
    timeout: float = 5.0,
) -> str:
    """Request one non-streaming completion from Ollama."""
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
            body = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise OllamaError(f"Ollama call to {model} failed: {exc}") from exc
    reply = body.get("response")
    if not isinstance(reply, str):
        raise OllamaError(f"Ollama returned no text for {model}: {body!r}")
    return reply


def ollama_asker(
    model: str = DEFAULT_MODEL,
    url: str = DEFAULT_URL,
    timeout: float = 5.0,
):
    """Return an injectable ``ask(prompt, system)`` function."""

    def ask(prompt: str, system: str = "") -> str:
        return ask_ollama(prompt, system, model=model, url=url, timeout=timeout)

    return ask
