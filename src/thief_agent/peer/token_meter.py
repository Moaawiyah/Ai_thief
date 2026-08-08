"""Token accounting helpers shared by runtime turn assembly and reports."""


def _sources(runtime) -> list:
    sources = [getattr(runtime, "llm", None), getattr(runtime, "hint_writer", None)]
    unique: list = []
    for source in sources:
        if source is not None and all(source is not item for item in unique):
            unique.append(source)
    return unique


def total(runtime) -> int:
    """Return cumulative tokens from every distinct configured model source."""
    return sum(int(getattr(source, "tokens_consumed", 0)) for source in _sources(runtime))


def step_usage(runtime, before: int) -> tuple[dict, int]:
    """Return the latest usage snapshot and the increase since a turn began."""
    after = total(runtime)
    delta = max(0, after - before)
    usages = [getattr(source, "last_usage", {}) for source in _sources(runtime)]
    usages = [usage for usage in usages if usage.get("total")]
    if not usages:
        return {"model": "heuristic", "in": 0, "out": 0, "total": delta}, delta
    model = "+".join(str(usage.get("model", "unknown")) for usage in usages)
    return {
        "model": model,
        "in": sum(int(usage.get("in", 0) or 0) for usage in usages),
        "out": sum(int(usage.get("out", 0) or 0) for usage in usages),
        "total": delta,
    }, delta


__all__ = ["step_usage", "total"]
