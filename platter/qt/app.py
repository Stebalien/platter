from PyQt5 import QtWidgets
from ..util import async
import os, threading

from .ui import PlatterQtUI
from ..server import Server

class PlatterQt(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


        self.server = Server()
        self.main = PlatterQtUI()
        self.connectSignals()

        fpaths = self.arguments()[1:]
        if fpaths:
            self.addFiles(fpaths)

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

