"""Local Ollama provider with structured output and token accounting.

Distinct from `infra/ollama.py` (free-text hint dialogue): this provider
implements the `send(prompt, timeout, schema)` interface used for constrained
movement-tactics selection (see `strategy/llm_tactics.py`), returning
JSON-schema-validated structured output rather than prose.
"""

import json
import urllib.error
import urllib.request

from thief_agent.exceptions import ProviderError, ProviderParseError, ProviderTimeoutError

_DEFAULT_URL = "http://127.0.0.1:11434/api/generate"
_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action_id": {"type": "string", "pattern": "^A[0-9]+$"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string", "maxLength": 300},
    },
    "required": ["action_id", "confidence", "reasoning"],
    "additionalProperties": False,
}

__all__ = ["OllamaLlmProvider"]


class OllamaLlmProvider:
    """Call one local model and expose usage through the common LLM interface."""

    def __init__(self, config):
        self._model = config.get("llm.model", "") or "qwen3:8b"
        self._url = config.get("llm.ollama_url", _DEFAULT_URL)
        self.last_usage = {"model": self._model, "in": 0, "out": 0, "total": 0}
        self.tokens_consumed = 0

    def send(self, prompt: str, timeout=None, schema=None) -> str:
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": schema or _ACTION_SCHEMA,
            "options": {"temperature": 0},
        }
        request = urllib.request.Request(  # noqa: S310 - configured local model endpoint
            self._url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout or 30) as response:  # noqa: S310
                wrapper = json.loads(response.read())
        except TimeoutError as exc:
            raise ProviderTimeoutError("Ollama request timed out") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ProviderParseError("Ollama returned invalid JSON") from exc
        text = wrapper.get("response")
        if not isinstance(text, str):
            raise ProviderParseError("Ollama response is missing model text")
        tokens_in = int(wrapper.get("prompt_eval_count", 0) or 0)
        tokens_out = int(wrapper.get("eval_count", 0) or 0)
        total = tokens_in + tokens_out
        self.last_usage = {"model": self._model, "in": tokens_in, "out": tokens_out, "total": total}
        self.tokens_consumed += total
        return text
