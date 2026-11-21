"""Синхронная шина событий Андреа."""

from collections import defaultdict, deque

__all__ = ["EventBus"]


class EventBus:
    def __init__(self):
        self.listeners = defaultdict(list)
        self.events = deque(maxlen=500)

    def subscribe(self, event_type, callback):
        self.listeners[event_type].append(callback)

    def emit(self, event_type, payload=None):
        payload = payload or {}
        self.events.append((event_type, payload))
        for key in (event_type, "*"):
            for cb in self.listeners[key]:
                cb(event_type, payload)

    def history(self, max_n=500):
        return list(self.events)[-max_n:]
