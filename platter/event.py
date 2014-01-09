from threading import Lock

class EventHandler:
    __slots__ = ("__callbacks",)

    def __init__(self):
        self.__callbacks = {}
        self._lock = Lock()

    def trigger(self, signal, *args, **kwargs):
        with self._lock:
            callbacks = self.__callbacks.get(signal, frozenset()).union(self.__callbacks.get("all", frozenset()))

        for cb in callbacks:
            cb(*args, **kwargs)

    def on(self, signal, cb):
        with self._lock:
            self.__callbacks.setdefault(signal, set()).add(cb)

    def off(self, signal, cb):
        with self._lock:
            if signal in self.__callbacks:
                self.__callbacks[signal].remove(cb)

    def once(self, signal, cb):
        def fn(*args, **kwargs):
            self.off(signal, cb)
            cb(*args, **kwargs)
        return self.on(signal, fn)
