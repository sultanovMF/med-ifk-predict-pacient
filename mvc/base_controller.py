from typing import Callable, cast

from .events import Event
from .subscriber import ISubscriber


class BaseController(ISubscriber):
    def __init__(self):
        self._event_handlers: dict[Event, Callable] = {}

    def update(self, event: Event):
        if type(event) in self._event_handlers:
            self._event_handlers[cast(Event, type(event))](event)
