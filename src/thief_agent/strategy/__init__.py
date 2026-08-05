"""Strategy seam with a heuristic default and mutually agreed LLM tactics.

Extend the shipped brain and override either hook:
  * `_pick_move(moves, state, belief)` — pick a legal move (the core heuristic); or
  * write a full policy by subclassing `ThiefBrain`.

When the signed shared config permits it, `strategy.mode = "llm"` lets the
model choose from a legality-checked, heuristic shortlist (`strategy/llm_tactics.py`).
Invalid or late model output falls back to the configured Python brain.

This package re-exports the base classes to extend (`BrainBase`, `ThiefBrain`,
`Decision`) and provides `resolve_brain`, the factory the SDK can use. It
honours an OPTIONAL config selector (`strategy.thief_class`, a dotted
`"package.module:ClassName"`) and otherwise uses the shipped heuristic brain.
"""

import importlib
import random

from thief_agent.domain.belief import BeliefGrid
from thief_agent.domain.brains import BrainBase, Decision, ThiefBrain
from thief_agent.exceptions import ConfigError
from thief_agent.strategy.talk_providers import resolve_trash_talk

__all__ = [
    "BeliefGrid",
    "BrainBase",
    "Decision",
    "ThiefBrain",
    "load_brain_cls",
    "resolve_brain",
    "resolve_brain_cls",
    "resolve_trash_talk",
]

_SELECTOR_KEY = "strategy.thief_class"


def load_brain_cls(dotted: str) -> type[BrainBase]:
    """Import a brain class from a ``"package.module:ClassName"`` selector.

    Raises ValueError on a malformed selector or a missing attribute, and
    TypeError when the target is not a `BrainBase` subclass.
    """
    module_path, sep, class_name = dotted.partition(":")
    if not sep or not module_path or not class_name:
        raise ValueError(f"strategy selector must be 'package.module:ClassName', got {dotted!r}")
    module = importlib.import_module(module_path)
    try:
        brain_cls = getattr(module, class_name)
    except AttributeError as exc:
        raise ValueError(f"{class_name!r} not found in module {module_path!r}") from exc
    if not (isinstance(brain_cls, type) and issubclass(brain_cls, BrainBase)):
        raise TypeError(f"{dotted!r} does not name a BrainBase subclass")
    return brain_cls


def resolve_brain_cls(config) -> type[BrainBase]:
    """Return the Thief brain class: the config selector if set, else the
    shipped default (`ThiefBrain`)."""
    selector = config.get(_SELECTOR_KEY) if config is not None else None
    if selector:
        return load_brain_cls(str(selector))
    return ThiefBrain


def resolve_brain(config, llm=None, rng: random.Random | None = None) -> BrainBase:
    """Instantiate the resolved brain, opting into constrained LLM tactics when
    `strategy.mode = "llm"` and the shared config permits it.

    With no `[strategy]` selector this is the shipped heuristic brain; movement
    is never LLM-driven unless explicitly enabled here."""
    rng = rng or random.Random()
    brain = resolve_brain_cls(config)()
    mode = str(config.get("strategy.mode", "heuristic")).lower()
    if mode not in {"heuristic", "llm"}:
        raise ConfigError("strategy.mode must be 'heuristic' or 'llm'")
    if mode == "llm":
        if not config.get("strategy.llm_tactics_allowed", False):
            raise ConfigError("LLM tactics require mutual signed consent in game.json")
        from thief_agent.strategy.llm_tactics import CONTRACT_VERSION, LlmTactics

        agreed = str(config.get("strategy.llm_contract_version", ""))
        if agreed != CONTRACT_VERSION:
            raise ConfigError(f"LLM tactics contract must be {CONTRACT_VERSION!r}, got {agreed!r}")
        if llm is None:
            raise ConfigError("strategy.mode='llm' requires an llm provider")
        brain.enable_tactics(LlmTactics(config, llm))
    return brain
