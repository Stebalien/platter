class EventHandler:
    def __init__(self):
        self.callbacks = {}

    def trigger(self, signal, *args, **kwargs):
        for cb in self.callbacks.get(signal, ()):
            cb(*args, **kwargs)
        for cb in self.callbacks.get("all", ()):
            cb(signal, *args, **kwargs)

    def on(self, signal, cb):
        self.callbacks.setdefault(signal, set()).add(cb)

    def off(self, signal, cb):
        if signal in self.callbacks:
            self.callbacks[signal].remove(cb)

