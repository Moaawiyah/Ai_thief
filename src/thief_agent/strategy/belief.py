"""Compatibility re-export: belief now lives at domain level (mirrors Police)."""

from thief_agent.domain.belief import (
    DEFAULT_LEAK,
    DEFAULT_SMELL_POWER,
    DEFAULT_SMELL_TRUST,
    BeliefGrid,
)

__all__ = ["BeliefGrid", "DEFAULT_LEAK", "DEFAULT_SMELL_POWER", "DEFAULT_SMELL_TRUST"]
