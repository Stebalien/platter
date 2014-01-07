import threading, qrcode
from PyQt5 import QtGui, QtCore, QtWidgets
from .util import async
from .server import PlatterHTTPServer
from cgi import escape
from urllib.request import pathname2url
import os

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
    return Signaler(fn, block)

class IllegalArgumentException(ValueError):
    pass

def path2url(path):
    return 'file://' + pathname2url(os.path.abspath(path))

class PlatterQt(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #try:
        #    fname = self.arguments()[1]
        #except:
        #    raise IllegalArgumentException("Missing Filename")

        #if not os.path.exists(fname):
        #    raise IllegalArgumentException("File Not Found: %s" % fname)


        self.server = PlatterHTTPServer()
        self.main = PlatterQtUI()
        self.connectSignals()

        for fpath in self.arguments()[1:]:
            self.addFile(fpath)

        self.main.show()

        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def connectSignals(self):
        self.aboutToQuit.connect(self.onQuit)

    def onQuit(self):
        self._shutdown()

    def addFile(self, fpath):
        if os.path.exists(fpath):
            self.server.serve(fpath)
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

class PlatterQtUI(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.app = QtWidgets.QApplication.instance()
        QtGui.QIcon.setThemeName('Faenza')
        self.file_panes = {}

        self.initUI()
        self.connectSignals()

    def connectSignals(self):
        self.app.server.on("add", sync(self.onAddFile))
        self.app.server.on("remove", sync(self.onRemoveFile))

    def dragEnterEvent(self, event):
        if all(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            self.app.addFile(url.path())

    def initUI(self):
        self.setAcceptDrops(True);
        self.setWindowFlags(QtCore.Qt.Dialog)
        frame = self.frameGeometry()
        frame.moveCenter(self.app.desktop().availableGeometry().center())
        self.move(frame.topLeft())
        
        # Build pane
        self.content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setContentsMargins(0,0,0,0)
        content_layout.addLayout(self.makeFilesPane())
        content_layout.addStretch(1)
        content_layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.content.setLayout(content_layout)
        self.content.hide()

        self.notice = QtWidgets.QLabel("Drag to serve files...")
        self.notice.setMinimumSize(200, 150)
        self.notice.setAlignment(QtCore.Qt.AlignCenter)

        window_layout = QtWidgets.QHBoxLayout(self)
        window_layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        window_layout.addWidget(self.content)
        window_layout.addWidget(self.notice)

        self.setLayout(window_layout)
        self.setWindowTitle('Platter')

    def makeFilesPane(self):
        files_container = QtWidgets.QWidget()
        self.files_pane = QtWidgets.QVBoxLayout()
        self.files_pane.setSpacing(0)
        self.files_pane.setContentsMargins(0,0,0,0)
        self.files_pane.addStretch(1)

        return self.files_pane

    def onAddFile(self, f):
        file_pane = FilePane(f)
        self.file_panes[f] = file_pane
        self.files_pane.addWidget(file_pane)
        self.content.show()
        self.notice.hide()

    def onRemoveFile(self, f):
        file_pane = self.file_panes.pop(f)
        self.files_pane.removeWidget(file_pane)
        v = file_pane.layout().takeAt(0)
        while v:
            w = v.widget()
            if w:
                w.hide()
            v = file_pane.layout().takeAt(0)

        if not self.file_panes:
            self.notice.show()
            self.content.hide()

    def closeEvent(self, e):
        e.ignore()
        self.app.shutdown()
        self.notice.setText("Shutting down...")
        self.content.hide()
        self.notice.show()

    def keyPressEvent(self, e):
        if e.key() in (QtCore.Qt.Key_Escape, QtCore.Qt.Key_Q):
            self.close()

class FilePane(QtWidgets.QWidget):

    def __init__(self, f):
        super().__init__()
        self.app = QtWidgets.QApplication.instance()
        self.transfer_panes = {}
        self.file = f

        self.initUI()
        self.connectSignals()

    def connectSignals(self):
        self.file.on("add", sync(self.onAddTransfer, True))
        self.file.on("remove", sync(self.onRemoveTransfer))

    def initUI(self):
        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setContentsMargins(5,5,5,5)
        content_layout.addLayout(self.makeQRCode())
        content_layout.addLayout(self.makeInfoPane())
        content_layout.addStretch(1)
        content_layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.setLayout(content_layout)

    def makeQRCode(self):
        image = qrcode.make(self.file.url, box_size=5)
        pixmap = QtGui.QPixmap.fromImage(QtGui.QImage(image.tobytes(), image.size[0], image.size[1], QtGui.QImage.Format_Mono))
        label = QtWidgets.QLabel('', self)
        label.setPixmap(pixmap)
        container = QtWidgets.QVBoxLayout()
        container.addWidget(label)
        container.addStretch(1)
        return container

    def makeHeaderPane(self):
        title = QtWidgets.QLabel(
            '<a style="color: {color};" href="{url}"><h1 style="font-weight: normal;">{filename}</h1></a>'.format(
                filename=escape(self.file.basename),
                url=path2url(self.file.filepath),
                color=self.palette().brightText().color().name()
            )
        )
        title.setOpenExternalLinks(True)

        removeBtn = QtWidgets.QToolButton()
        removeBtn.setText('Remove')
        removeBtn.setIcon(QtGui.QIcon.fromTheme("edit-delete"))
        removeBtn.clicked.connect(self.onRemove)

        header = QtWidgets.QHBoxLayout()
        header.addWidget(title)
        header.addWidget(removeBtn)

        return header

    def onRemove(self):
        self.file.stop()

    def makeInfoPane(self):
        pane = QtWidgets.QVBoxLayout()
        pane.addLayout(self.makeHeaderPane())
        pane.addLayout(self.makeUrlPane())
        pane.addWidget(self.makeTransfersPane())
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

    def makeTransfersPane(self):
        transfers_container = QtWidgets.QWidget()
        self.transfers_pane = QtWidgets.QVBoxLayout()
        self.transfers_pane.setSpacing(0)
        self.transfers_pane.setContentsMargins(0,0,0,0)
        self.transfers_pane.addStretch(1)

        outer_layout = QtWidgets.QVBoxLayout()
        outer_layout.addLayout(self.transfers_pane)
        outer_layout.addStretch(1)
        transfers_container.setLayout(outer_layout)

        scroll_container = QtWidgets.QScrollArea()
        scroll_container.setWidget(transfers_container)
        scroll_container.setWidgetResizable(True)
        return scroll_container

    def copyToClipboard(self):
        self.app.clipboard().setText(self.file.url)

    def onAddTransfer(self, request):
        transfer = TransferPane(request)
        self.transfer_panes[request] = transfer
        self.transfers_pane.addWidget(transfer)

    def onRemoveTransfer(self, request):
        transfer = self.transfer_panes.pop(request)
        self.transfers_pane.removeWidget(transfer)
        v = transfer.layout().takeAt(0)
        while v:
            v.widget().hide()
            v = transfer.layout().takeAt(0)


class TransferPane(QtWidgets.QWidget):
    def __init__(self, request):
        super().__init__()
        self.app = QtWidgets.QApplication.instance()
        self.request = request

        self.initUI()
        self.connectSignals()

    def initUI(self):
        self.progress_bar = QtWidgets.QProgressBar()

        self.progress_bar.setFormat("{}:{} - %p%".format(*self.request.client_address))
        self.progress_bar.setValue(self.request.progress)
        self.progress_bar.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

        self.close_button = QtWidgets.QToolButton()
        self.close_button.setIcon(QtGui.QIcon.fromTheme("window-close"))


        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.close_button)
        self.setLayout(layout)


    def connectSignals(self):
        self.request.on("progress", sync(self.onProgress))
        self.request.on("success", sync(self.onSucceed))
        self.request.on("fail", sync(self.onFailure))

        self.close_button.clicked.connect(self.onCancel)

    def onProgress(self, progress):
        self.progress_bar.setValue(progress)

    def onSucceed(self):
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("{}:{} - Completed".format(*self.request.client_address))

    def onFailure(self):
        self.progress_bar.setFormat("{}:{} - Failed".format(*self.request.client_address))
    
    def onCancel(self):
        self.request.cancel()

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
