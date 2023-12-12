from dataclasses import dataclass

from mvc import Event


@dataclass
class UserNotifyEvent(Event):
    pass


@dataclass
class ReinitializeHandlersEvent(Event):
    pass


@dataclass
class UpdateUserFormEvent(Event):
    pass


@dataclass
class SaveUserFormEvent(Event):
    pass


@dataclass
class NewUserFormEvent(Event):
    pass


@dataclass
class UpdateMarkEvent(Event):
    pass

