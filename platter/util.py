import os, base64
import threading
import itertools

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


def list_files(path):
    if os.path.isdir(path):
        return itertools.chain.from_iterable((
            os.path.join(dirpath, f)
            for f in filenames
        ) for dirpath, dirnames, filenames in os.walk(path))
    else:
        return (path,)

