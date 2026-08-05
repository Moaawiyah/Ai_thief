"""Compatibility re-export: the base brain now lives at domain level (mirrors
Police). See strategy/team_strategy.py for the example extension subclass."""

from thief_agent.domain.brains import BrainBase, Decision, ThiefBrain

__all__ = ["BrainBase", "Decision", "ThiefBrain"]
