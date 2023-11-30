from dataclasses import dataclass

from .event import Event


@dataclass
class UserModel:
    current_event: Event
    form: {}
