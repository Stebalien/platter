from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from .event import EventHandler
from .network import find_ip
import os
from urllib.parse import quote

from .util import make_code

BUF_SIZE = 16*1024

class PlatterHTTPRequestHandler(BaseHTTPRequestHandler, EventHandler):
    canceled = False
    progress = 0
    def __init__(self, *args, **kwargs):
        EventHandler.__init__(self)
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
    def do_GET(self):
        try:
            self.file = self.server.paths[self.path]
        except:
            self.send_error(404)
            return
        
        try:
            self.file._register_request(self)
            self.send_response(200)

            self.trigger("start")

            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", "attachment;filename=%s" % quote(self.file.basename))
            self.send_header('Content-Length', self.file.size)
            self.end_headers()


            percent_increment = float(BUF_SIZE)/float(self.file.size)*100

            with open(self.file.filepath, 'rb') as fobj:
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

class File(EventHandler):
    def __init__(self, server, filepath):
        super().__init__()

        self.server = server
        self.requests = set()

        self.filepath = filepath
        self.basename = os.path.basename(filepath)
        self.path = "/" + make_code()
        self.size = os.path.getsize(filepath)

        self.server.files[self.filepath] = self
        self.server.paths[self.path] = self

    @property
    def url(self):
        return "http://%s:%d%s" % (
            self.server.my_ip, self.server.server_port, self.path
        )
    
    def stop(self):
        self.server.unserve(self.filepath)

        for req in frozenset(self.requests):
            req.cancel()


    def _register_request(self, request):
        # Assume that devices only download once (to work around chromes double get)
        self.requests.add(request)
        self.trigger("add", request)

    def _unregister_request(self, request):
        self.requests.remove(request)
        self.trigger("remove", request)


class PlatterHTTPServer(ThreadingMixIn, HTTPServer, EventHandler):

    def __init__(self, address=("", 0), handler=PlatterHTTPRequestHandler, **kwargs):
        EventHandler.__init__(self)
        HTTPServer.__init__(self, address, handler, **kwargs)
        self.paths = {}
        self.files = {}
        self.my_ip = find_ip()

    def serve(self, fpath):
        if fpath in self.files:
            f = self.files[fpath]
        else:
            f = File(self, fpath)
            self.files[f.filepath] = f
            self.paths[f.path] = f

        self.trigger("add", f)
        return f
    
    def unserve(self, fpath):
        if fpath in self.files:
            f = self.files.pop(fpath)
            del self.paths[f.path]
            self.trigger("remove", f)

