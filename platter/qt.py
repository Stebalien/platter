import threading, qrcode
from PyQt5 import QtGui, QtCore, QtWidgets
from .util import async
from .server import PlatterHTTPServer
from cgi import escape
import os


class IllegalArgumentException(ValueError):
    pass

class PlatterQt(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            fname = self.arguments()[1]
        except:
            raise IllegalArgumentException("Missing Filename")

        if not os.path.exists(fname):
            raise IllegalArgumentException("File Not Found: %s" % fname)

        self.transfers = {}

        self.server = PlatterHTTPServer()

        self.file = self.server.serve(fname)

        self.main = PlatterQtUI(self.file)
        self.connectSignals()

        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def connectSignals(self):
        self.file.on("progress", self.proxyProgress)
        self.file.on("failure", self.proxyFailure)
        self.file.on("success", self.proxySuccess)
        self.file.on("start", self.proxyStart)
        self.aboutToQuit.connect(self.onQuit)

    def onQuit(self):
        self._shutdown()

    def _shutdown(self):
        self.server.shutdown()
        self.server_thread.join()

    @async
    def shutdown(self):
        self._shutdown()
        self.quit()

    def proxyStart(self, transfer):
        self.main.addTransferSignal.emit(transfer)

    def proxyProgress(self, transfer, progress):
        try:
            pane = self.transfers[transfer.client_address[0]]
        except KeyError:
            return
        pane.progressSignal.emit(progress)

    def proxySuccess(self, transfer):
        try:
            pane = self.transfers[transfer.client_address[0]]
        except KeyError:
            return
        pane.successSignal.emit()

    def proxyFailure(self, transfer):
        try:
            pane = self.transfers[transfer.client_address[0]]
        except KeyError:
            return
        pane.failureSignal.emit()

class PlatterQtUI(QtWidgets.QWidget):
    addTransferSignal = QtCore.pyqtSignal(object)
    quitSignal = QtCore.pyqtSignal()

    def __init__(self, f):
        super().__init__()
        self.app = QtWidgets.QApplication.instance()
        QtGui.QIcon.setThemeName('Faenza')

        self.file = f

        self.initUI()
        self.connectSignals()

    def connectSignals(self):
        self.addTransferSignal.connect(self.onAddTransfer, QtCore.Qt.BlockingQueuedConnection)
        #self.quitSignal.connect(self.onQuit)

    def initUI(self):
        #self.setGeometry(300, 300, 250, 150)
        self.setWindowFlags(QtCore.Qt.Dialog)
        frame = self.frameGeometry()
        frame.moveCenter(self.app.desktop().availableGeometry().center())
        self.move(frame.topLeft())

        
        # Build pane
        self.content = QtWidgets.QWidget()
        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setContentsMargins(0,0,0,0)
        content_layout.addLayout(self.makeQRCode())
        content_layout.addLayout(self.makeInfoPane())
        content_layout.addStretch(1)
        content_layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.content.setLayout(content_layout)

        window_layout = QtWidgets.QHBoxLayout(self)
        window_layout.addWidget(self.content)

        self.setLayout(window_layout)
        self.setWindowTitle('Platter')
        self.show()

    def makeQRCode(self):
        image = qrcode.make(self.file.url, box_size=5)
        pixmap = QtGui.QPixmap.fromImage(QtGui.QImage(image.tobytes(), image.size[0], image.size[1], QtGui.QImage.Format_Mono))
        label = QtWidgets.QLabel('', self)
        label.setPixmap(pixmap)
        container = QtWidgets.QVBoxLayout()
        container.addWidget(label)
        container.addStretch(1)
        return container

    def makeInfoPane(self):
        title = QtWidgets.QLabel('<h1 style="font-weight: normal;">{filename}</h1>'.format(
            filename=escape(self.file.basename),
        ))

        pane = QtWidgets.QVBoxLayout()
        pane.addWidget(title)
        pane.addLayout(self.makeUrlPane())
        pane.addWidget(self.makeTransferPane())
        return pane

    def makeUrlPane(self):
        url = QtWidgets.QLabel(self.file.url)
        copyLink = QtWidgets.QToolButton()
        copyLink.setText('Copy')
        copyLink.setIcon(QtGui.QIcon.fromTheme("edit-copy"))
        copyLink.clicked.connect(self.copyToClipboard)

        url_pane = QtWidgets.QHBoxLayout()
        url_pane.addWidget(url)
        url_pane.addWidget(copyLink)
        url_pane.addStretch(1)
        return url_pane

    def makeTransferPane(self):
        transfer_container = QtWidgets.QWidget()
        self.transfer_pane = QtWidgets.QVBoxLayout()
        self.transfer_pane.setSpacing(0)
        self.transfer_pane.setContentsMargins(0,0,0,0)
        self.transfer_pane.addStretch(1)

        outer_layout = QtWidgets.QVBoxLayout()
        outer_layout.addLayout(self.transfer_pane)
        outer_layout.addStretch(1)
        transfer_container.setLayout(outer_layout)

        scroll_container = QtWidgets.QScrollArea()
        scroll_container.setWidget(transfer_container)
        scroll_container.setWidgetResizable(True)
        return scroll_container

    def copyToClipboard(self):
        self.app.clipboard().setText(self.file.url)

    def onAddTransfer(self, request):
        address = str(request.client_address[0])
        # Assume that devices only download once (to work around chromes double get)
        if address in self.app.transfers:
            transfer = self.app.transfers[address]
        else:
            transfer = TransferPane(address)
            self.app.transfers[address] = transfer
            self.transfer_pane.addWidget(transfer)
        transfer.addRequest(request)
        transfer.onStart()

    def insertTrans(self, widget):
        self.transfer_pane.addWidget(widget)

    def closeEvent(self, e):
        self.app.shutdown()
        e.ignore()
        self.layout().takeAt(0).widget().hide()
        label = QtWidgets.QLabel("Shutting down...")
        label.setAlignment(QtCore.Qt.AlignCenter)
        self.layout().addWidget(label)


    def keyPressEvent(self, e):
        if e.key() in (QtCore.Qt.Key_Escape, QtCore.Qt.Key_Q):
            self.close()

class TransferPane(QtWidgets.QWidget):
    progressSignal = QtCore.pyqtSignal(int)
    successSignal = QtCore.pyqtSignal()
    failureSignal = QtCore.pyqtSignal()
    def __init__(self, address):
        super().__init__()
        self.app = QtWidgets.QApplication.instance()
        self.address = address
        self.requests = []

        self.initUI()
        self.connectSignals()

    def initUI(self):
        self.progress_bar = QtWidgets.QProgressBar()

        self.close_button = QtWidgets.QToolButton()
        self.close_button.setIcon(QtGui.QIcon.fromTheme("window-close"))
        self.close_button.clicked.connect(self.remove)


        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.close_button)
        self.setLayout(layout)

    def connectSignals(self):
        self.progressSignal.connect(self.onProgress)
        self.successSignal.connect(self.onSucceed)
        self.failureSignal.connect(self.onFailure)

    def onProgress(self, progress):
        self.progress_bar.setValue(progress)

    def onStart(self):
        self.progress_bar.setFormat("{address} - %p%".format(address=self.address))
        self.progress_bar.setValue(0)

    def addRequest(self, request):
        self.requests.append(request)

    def onSucceed(self):
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("{address} - Completed".format(address=self.address))

    def onFailure(self):
        self.progress_bar.setFormat("{address} - Failed".format(address=self.address))
    
    def remove(self):
        for request in self.requests:
            request.cancel()

        self.app.main.transfer_pane.removeWidget(self)
        del self.app.transfers[self.address]
        v = self.layout().takeAt(0)
        while v:
            v.widget().hide()
            v = self.layout().takeAt(0)


def main():
    import sys
    try:
        app = PlatterQt(sys.argv)
    except IllegalArgumentException as e:
        print(e, file=sys.stderr)
        return 1
    else:
        return app.exec()

if __name__ == "__main__":
    main()
