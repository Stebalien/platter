class EventHandler:
    __slots__ = ("__callbacks",)

    def __init__(self):
        self.__callbacks = {}

    def trigger(self, signal, *args, **kwargs):
        for cb in self.__callbacks.get(signal, ()):
            cb(*args, **kwargs)
        for cb in self.__callbacks.get("all", ()):
            cb(signal, *args, **kwargs)

    def on(self, signal, cb):
        self.__callbacks.setdefault(signal, set()).add(cb)

    def off(self, signal, cb):
        if signal in self.__callbacks:
            self.__callbacks[signal].remove(cb)

