from abc import ABCMeta, abstractmethod

from .events import Event
from .subscriber import ISubscriber


class IPublisher(metaclass=ABCMeta):
    @abstractmethod
    def subscribe(self, subscriber: ISubscriber):
        pass

    @abstractmethod
    def unsubscribe(self, subscriber: ISubscriber):
        pass

    @abstractmethod
    def publish(self, event: Event):
        pass
