"""Human-readable verbal mode labels for live and replay views."""

TEMPLATE_MODE = "Python (template)"
OLLAMA_MODE = "Ollama (local)"
REMOTE_MODE = "Remote LLM"
NO_MODEL = "None"
DEFAULT_OLLAMA_MODEL = "qwen3:4b"
_NO_MODEL_STRINGS = frozenset({"", "-", "none", "template", "stub"})


def mode_and_model(config) -> tuple[str, str]:
    read = config.get if config is not None else (lambda key, default=None: default)
    provider = str(read("trash_talk.provider", "template") or "template").lower()
    model = str(read("trash_talk.model", "") or "")
    if provider == "ollama":
        return OLLAMA_MODE, model or DEFAULT_OLLAMA_MODEL
    if provider == "template":
        return TEMPLATE_MODE, NO_MODEL
    return REMOTE_MODE, model or str(read("llm.model", "") or provider)


def mode_from_recorded_model(model: str) -> tuple[str, str]:
    text = str(model or "").strip()
    if text.lower() in _NO_MODEL_STRINGS:
        return TEMPLATE_MODE, NO_MODEL
    return REMOTE_MODE, text
