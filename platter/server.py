from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from .event import EventHandler
from .network import find_ip
import os
from urllib.parse import quote

from .util import make_code

BUF_SIZE = 16*1024

class PlatterHTTPRequestHandler(BaseHTTPRequestHandler):
    canceled = False
    def do_GET(self):
        try:
            f = self.server.paths[self.path]
        except:
            self.send_error(404)
            return

        try:
            f.trigger("start", self)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", "attachment;filename=%s" % quote(f.basename))
            self.send_header('Content-Length', f.size)
            self.end_headers()

            percent_increment = float(BUF_SIZE)/float(f.size)*100
            percent_complete = 0

            with open(f.filepath, 'rb') as fobj:
                while True:
                    buf = fobj.read(BUF_SIZE)
                    if not buf:
                        break
                    if self.canceled:
                        return
                    self.wfile.write(buf)
                    percent_complete += percent_increment
                    f.trigger("progress", self, percent_complete)
        except:
            f.trigger("failure", self)
        else:
            f.trigger("success", self)

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

class File(EventHandler):
    def __init__(self, server, filepath):
        super().__init__()

        self.server = server

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

class PlatterHTTPServer(ThreadingMixIn, HTTPServer):

    def __init__(self, address=("", 0), handler=PlatterHTTPRequestHandler, **kwargs):
        HTTPServer.__init__(self, address, handler, **kwargs)
        self.paths = {}
        self.files = {}
        self.my_ip = find_ip()

    def serve(self, fpath):
        if fpath in self.files:
            return self.files[fpath]
        else:
            return File(self, fpath)
