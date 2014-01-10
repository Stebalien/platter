from PyQt5 import QtCore
import functools

__all__ = ("sync", "IllegalArgumentException")

class Signaler(QtCore.QObject):
    signal = QtCore.pyqtSignal(tuple, dict)

    def __init__(self, fn, block=False):
        super().__init__()

        self.function = fn
        if block:
            self.signal.connect(self.__handler, QtCore.Qt.BlockingQueuedConnection)
        else:
            self.signal.connect(self.__handler)

    def __handler(self, args, kwargs):
        self.function(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        self.signal.emit(args, kwargs)

def sync(fn, block=False):
    return functools.update_wrapper(Signaler(fn, block), fn)

class IllegalArgumentException(ValueError):
    pass

