"""Enums."""

from enum import StrEnum, auto


class NautobotEnvironment(StrEnum):
    """NautobotEnvironment Enum."""

    LOCAL = auto()
    LAB = auto()
    NONPROD = auto()
    PROD = auto()
