from abc import ABCMeta, abstractmethod

from .events import Event


class ISubscriber(metaclass=ABCMeta):
    @abstractmethod
    def update(self, event: Event):
        pass
