"""Resolve the grounded trash-talk provider from the [trash_talk] config block,
and the network 'askers' for the opt-in LLM providers.

This is an alternate, richer resolver (mirrors the Police peer's
`talk_providers.resolve_trash_talk`) alongside — not replacing — Thief's
default `strategy/talk.py:resolve_hint_writer`.

Providers:
  * ``template``    (default) - pure Python, zero tokens, instant, offline.
  * ``claude_cli``  - reuse the peer's Claude CLI provider (see infra/llm_provider.py).
  * ``claude_api``  - the Anthropic SDK with a SMALL model (default Haiku).
  * ``ollama``      - a local model via the Ollama HTTP API - free, no RPM limit.
"""

import json
import logging
import random
import urllib.request

from thief_agent.strategy.llm_hints import HINT_SCHEMA, LlmTrashTalk
from thief_agent.strategy.trash_talk import TrashTalk

logger = logging.getLogger(__name__)

_OLLAMA_DEFAULT = "http://localhost:11434/api/generate"

__all__ = ["resolve_trash_talk"]


def resolve_trash_talk(config, rng: random.Random, llm=None) -> TrashTalk:
    """Build the trash-talk provider. Default (and any unknown value) is the free
    ``template`` provider, so the shipped game runs fast and offline."""
    get = config.get if config is not None else (lambda _k, d=None: d)
    provider = str(get("trash_talk.provider", "template")).lower()
    every = get("trash_talk.every_n_steps", 1)
    model = get("trash_talk.model", "")
    confidence = get("trash_talk.min_confidence", 0.55)
    max_words = get("play.hint_max_words", 15)  # negotiated hard cap (world.hint_max_words)

    if provider == "template":
        return TrashTalk(rng, max_words)
    if provider in {"claude_cli", "ollama"} and llm is not None:

        def shared_ask(prompt, deadline=None, system=""):
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            try:
                return llm.send(full_prompt, timeout=deadline, schema=HINT_SCHEMA)
            except TypeError:
                return llm.send(full_prompt)

        return LlmTrashTalk(shared_ask, rng, every, model, max_words, confidence)
    if provider == "claude_cli" and llm is None:
        logger.warning("trash_talk.provider=claude_cli but no llm; using template")
        return TrashTalk(rng, max_words)
    if provider == "ollama":
        url = get("trash_talk.ollama_url", _OLLAMA_DEFAULT)
        return LlmTrashTalk(
            _ollama_asker(model or "qwen3:8b", url),
            rng,
            every,
            model,
            max_words,
            confidence,
        )
    if provider == "claude_api":
        return LlmTrashTalk(
            _claude_api_asker(model or "claude-haiku-4-5"),
            rng,
            every,
            model,
            max_words,
            confidence,
        )

    logger.warning("unknown trash_talk.provider %r; using template", provider)
    return TrashTalk(rng, max_words)


def _ollama_asker(model: str, url: str):
    """A local Ollama call (stdlib only, no extra dependency)."""

    def ask(prompt: str, deadline=None, system: str = "") -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": HINT_SCHEMA,
            "options": {"temperature": 0},
        }
        if system:
            payload["system"] = system  # Ollama's native system-prompt field
        body = json.dumps(payload).encode()
        request = urllib.request.Request(  # noqa: S310 - fixed localhost Ollama endpoint
            url, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=deadline or 30) as response:  # noqa: S310
            return json.loads(response.read())["response"]

    return ask


def _claude_api_asker(model: str):
    """A short Anthropic Messages API call using a SMALL model (default Haiku).
    `anthropic` is imported lazily so it stays an optional dependency."""

    def ask(prompt: str, deadline=None, system: str = "") -> str:
        import anthropic  # optional dep; only needed for provider=claude_api

        client = anthropic.Anthropic()
        kwargs = {
            "model": model,
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system  # Anthropic Messages API system prompt
        message = client.messages.create(**kwargs)
        return "".join(block.text for block in message.content if block.type == "text")

    return ask
