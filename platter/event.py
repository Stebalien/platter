from threading import Lock

__all__ = ("Observable",)

class Observable:
    __slots__ = ()

    def __init__(self):
        self.__callbacks = {}
        self.__lock = Lock()

    def trigger(self, signal, *args, **kwargs):
        with self.__lock:
            callbacks = self.__callbacks.get(
                signal, frozenset()
            ).union(self.__callbacks.get(
                "all", frozenset()
            ))

        for cb in callbacks:
            cb(*args, **kwargs)

    def on(self, signal, cb):
        with self.__lock:
            self.__callbacks.setdefault(signal, set()).add(cb)

    def off(self, signal, cb):
        with self.__lock:
            if signal in self.__callbacks:
                self.__callbacks[signal].remove(cb)

    def once(self, signal, cb):
        def fn(*args, **kwargs):
            self.off(signal, cb)
            cb(*args, **kwargs)
        return self.on(signal, fn)
