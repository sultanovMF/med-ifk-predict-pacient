from mvc.events import Event
from mvc.publisher import IPublisher
from mvc.subscriber import ISubscriber


class EventBus(IPublisher):
    def __init__(self):
        from mvc import ISubscriber

        self.__subscribers: list[ISubscriber] = []

    def subscribe(self, subscriber: ISubscriber):
        self.__subscribers.append(subscriber)

    def unsubscribe(self, subscriber: ISubscriber):
        self.__subscribers.remove(subscriber)

    def publish(self, event: Event):
        for subscriber in self.__subscribers:
            subscriber.update(event)
