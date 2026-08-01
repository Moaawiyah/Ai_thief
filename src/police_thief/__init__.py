"""Thief peer entrypoint and repository identity."""

from police_thief.constants import Role

ROLE = Role.THIEF


def main() -> None:
    print("Hello from thief!")
