from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from threading import Thread, Event
from .event import Observable
from tempfile import TemporaryFile
from .network import find_ip
import os
from urllib.parse import quote
from io import DEFAULT_BUFFER_SIZE as BUF_SIZE
import itertools
from zipfile import ZipFile

from .util import list_files

__all__ = ("Observable",)

def render_multiget(fids):
    return "<p>Downlaoding Files...</p>" + "<br>".join(
        '<iframe style="border: none;" height="0" src="/{url}"><a href="/{url}">url</a></iframe>'.format(url=fid) for fid in fids
    )+"<script>window.open('', '_parent', ''); window.close();</script>"

class Request(BaseHTTPRequestHandler, Observable):
    canceled = False
    progress = 0
    def __init__(self, *args, **kwargs):
        Observable.__init__(self)
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def do_GET(self):

        # Multiget
        try:
            fids = set(itertools.chain.from_iterable((range(int(pair[0]), int(pair[1])+1) if len(pair) == 2 else (int(pair[0]),) for pair in (piece.split('-', 1) for piece in self.path[1:].split('+')))))
        except:
            self.send_error(404)
            return

        if not all(fid > 0 for fid in fids):
            self.send_error(404)
            return

        if len(fids) > 1:
            content = render_multiget(fids).encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
            return

        try:
            self.file = self.server.files[tuple(fids)[0]]
        except:
            self.send_error(404)
            return
        
        try:
            self.file._register_request(self)
            self.send_response(200)

            self.file.wait()

            self.trigger("start")

            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", "attachment;filename=%s" % quote(self.file.name))
            self.send_header('Content-Length', self.file.size)
            self.end_headers()


            percent_increment = float(BUF_SIZE)/float(self.file.size)*100

            with self.file.open() as fobj:
                while True:
                    buf = fobj.read(BUF_SIZE)
                    if not buf:
                        break
                    if self.canceled:
                        return
                    self.wfile.write(buf)
                    self.progress += percent_increment
                    self.trigger("progress", self.progress)
        except:
            self.trigger("failure")
        else:
            self.progress = 100
            self.trigger("success")


    def cancel(self):
        self.canceled = True
        if not self.wfile.closed:
            try:
                self.wfile.close()
            except:
                pass
        if not self.rfile.closed:
            try:
                self.rfile.close()
            except:
                pass
        self.file._unregister_request(self)

class File(Observable):
    size = None

    def __init__(self, server, fid, name):
        super().__init__()

        self.fid = fid
        self.server = server
        self.requests = set()
        self._loaded = Event()

        self.name = name

    def open(self):
        raise NotImplementedError()

    @property
    def url(self):
        return "http://%s:%d/%d" % (
            self.server.my_ip, self.server.server_port, self.fid
        )

    @property
    def loaded(self):
        return self._loaded.is_set()

    def wait(self):
        self._loaded.wait()
    
    def stop(self):
        self.server.unserve(self)

        for req in frozenset(self.requests):
            req.cancel()
        self.trigger("unload")

    def _register_request(self, request):
        # Assume that devices only download once (to work around chromes double get)
        self.requests.add(request)
        self.trigger("add", request)

    def _unregister_request(self, request):
        self.requests.remove(request)
        self.trigger("remove", request)

class RealFile(File):
    def __init__(self, server, fid, name):
        File.__init__(self, server, fid, name)

        self._size = None
        self._filepath = None

    def open(self):
        try:
            return open(self._filepath, "rb")
        except AttributeError:
            raise IOError("File not loaded")
    
    @property
    def size(self):
        if self.loaded and self._size is None:
            self._size = os.path.getsize(self._filepath)
        return self._size

    def _finish(self, filepath):
        self._filepath = filepath
        self._loaded.set()
        self.trigger("load")

class LocalFile(RealFile):
    def __init__(self, server, fid, filepath):
        super().__init__(server, fid, os.path.basename(filepath))
        self._finish(filepath)

class MultiFile(Thread, RealFile):
    def __init__(self, server, fid, name, files):
        Thread.__init__(self)
        RealFile.__init__(self, server, fid, name)

        self._files = files
        self.start()

    def run(self):
        files_with_size = [(path, os.path.getsize(path)) for path in self._files]
        total_size = sum(s for f,s in files_with_size)
        cur_size = 0
        file = TemporaryFile(mode='wb')
        with ZipFile(file, mode='w') as zipfile:
            for fpath,size in files_with_size:
                zipfile.write(fpath)
                cur_size += size
                self.trigger('loading', (cur_size/total_size*100))

        self.once("unload", lambda: file.close())
        self._finish("/proc/self/fd/%d" % file.fileno())

last_file_number = 0
def AutoFile(server, fid, fpaths):
    global last_file_number
    if len(fpaths) == 0:
        raise ValueError("No files specified")
    elif len(fpaths) == 1:
        if os.path.isdir(fpaths[0]):
            directory = fpaths[0]
            return MultiFile(server, fid, os.path.basename(directory)+".zip", list(list_files(directory)))
        else:
            return LocalFile(server, fid, fpaths[0])
    else:
        last_file_number += 1
        return MultiFile(
            server,
            fid, 
            "files-{}.zip".format(last_file_number),
            list(itertools.chain.from_iterable((
                list_files(path)
            ) for path in fpaths))
        )

class Server(ThreadingMixIn, HTTPServer, Observable):
    __last_fid = 0

    def __init__(self, address=("", 0), handler=Request, **kwargs):
        Observable.__init__(self)
        HTTPServer.__init__(self, address, handler, **kwargs)
        self.files = {}
        self.my_ip = find_ip()

    def serve(self, fpaths):
        self.__last_fid += 1
        f = AutoFile(self, self.__last_fid, fpaths)
        self.files[f.fid] = f
        self.trigger("add", f)

        return f
    
    def unserve(self, file):
        f = self.files.pop(file.fid)
        self.trigger("remove", f)

