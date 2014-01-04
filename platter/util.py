import os, base64
import threading

def make_code(length=6):
    return base64.urlsafe_b64encode(os.urandom(length)).decode('utf-8')

def async(func):
    def do(*args, **kwargs):
        if "callback" in kwargs:
            cb = kwargs.pop("callback")
            thread = threading.Thread(target=lambda: cb(func(*args, **kwargs)))
        else:
            thread = threading.Thread(target=lambda: func(*args, **kwargs))
        thread.start()
        return thread
    return do
