from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass
class Event:
    data: T


@dataclass
class TestEvent(Event):
    pass
