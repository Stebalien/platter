from PyQt5 import QtWidgets
from ..util import async
from ..dbus import get_instance, PlatterServerDBus
import os, threading
import argparse

from .ui import PlatterQtUI
from ..server import Server

class AlreadyRunning(Exception):
    pass

def parse_args(args):
    parser = argparse.ArgumentParser()
    def path_exists(string):
        if os.path.exists(string):
            return string
        else:
            raise argparse.ArgumentTypeError("Path '%s' does not exist." % string)

    parser.add_argument("files",
                        nargs='*',
                        type=path_exists,
                        default = [],
                       )
    parser.add_argument(
        "-a",
        "--archive",
        nargs='+',
        default = [],
        action='append',
        type=path_exists,
        dest="archives"
    )
    args = parser.parse_args()
    return [[fpath] for fpath in args.files] + args.archives


class PlatterQt(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            from dbus.mainloop.pyqt5 import DBusQtMainLoop
            DBusQtMainLoop(set_as_default=True)
        except ImportError:
            pass

        fpaths = parse_args(self.arguments()[1:])

        inst = get_instance()
        if inst:
            if fpaths:
                for fpath in fpaths:
                    inst.AddFiles(fpath)
                raise AlreadyRunning()


        self.server = Server()
        PlatterServerDBus(self.server)
        self.main = PlatterQtUI()
        self.connectSignals()

        if fpaths:
            for fpath in fpaths:
                self.addFiles(fpath)

        self.main.show()

        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def connectSignals(self):
        self.aboutToQuit.connect(self.onQuit)

    def onQuit(self):
        self._shutdown()

    def addFiles(self, fpaths):
        if all(os.path.exists(fpath) for fpath in fpaths):
            self.server.serve(fpaths)
            return True
        else:
            return False

    def _shutdown(self):
        self.server.shutdown()
        self.server_thread.join()

    @async
    def shutdown(self):
        self._shutdown()
        self.quit()

