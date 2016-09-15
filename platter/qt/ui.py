import qrcode
import qrcode.image.svg
from PyQt5 import QtGui, QtCore, QtWidgets, QtSvg
from io import BytesIO
from .common import sync

try:
    # Attempt to use gtk icon theme.
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    QtGui.QIcon.setThemeName(Gtk.Settings.get_default().get_property('gtk-icon-theme-name'))
except:
    # Fall back on default icon theme.
    QtGui.QIcon.setThemeName('default')

class PlatterQtUI(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.app = QtWidgets.QApplication.instance()
        self.file_panes = {}
        self.initUI()
        self.connectSignals()

    def connectSignals(self):
        self.app.server.on("add", sync(self.onAddFile))
        self.app.server.on("remove", sync(self.onRemoveFile))
        self.files_pane.tabCloseRequested.connect(self.onTabClose)
        self.add_file_button.clicked.connect(self.onAddFileButtonClicked)

    def dragEnterEvent(self, event):
        if all(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            self.app.addFiles([url.path() for url in event.mimeData().urls()])

    def onTabClose(self, index):
        self.files_pane.widget(index).file.stop()

    def initUI(self):
        self.setAcceptDrops(True);
        self.setWindowFlags(QtCore.Qt.Dialog)
        frame = self.frameGeometry()
        frame.moveCenter(self.app.desktop().availableGeometry().center())
        self.move(frame.topLeft())

        
        self.setLayout(self.makeFilesPane())
        self.setWindowTitle('Platter')
        self.setWindowIcon(QtGui.QIcon.fromTheme("top"))

    def makeFilesPane(self):
        self.files_pane = QtWidgets.QTabWidget()
        self.files_pane.setDocumentMode(True)
        self.add_file_button = QtWidgets.QPushButton()
        self.add_file_button.setStyleSheet("QPushButton { border: none; padding: 10px;}")
        self.add_file_button.setIcon(QtGui.QIcon.fromTheme("list-add"))
        self.files_pane.setCornerWidget(self.add_file_button)

        self.files_pane.setTabsClosable(True)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.files_pane)
        layout.setContentsMargins(0,0,0,0)
        return layout

    def onAddFileButtonClicked(self):
        files = QtWidgets.QFileDialog.getOpenFileNames(self, "Serve Files")[0]
        if files:
            self.app.addFiles(files)

    def onAddFile(self, f):
        file_pane = FilePane(f)
        self.file_panes[f] = file_pane
        self.files_pane.addTab(file_pane, f.name)

    def onRemoveFile(self, f):
        file_pane = self.file_panes.pop(f)
        self.files_pane.removeTab(self.files_pane.indexOf(file_pane))
        v = file_pane.layout().takeAt(0)
        while v:
            w = v.widget()
            if w:
                w.hide()
            v = file_pane.layout().takeAt(0)

        if not self.file_panes:
            self.close()

    def closeEvent(self, e):
        self.app.shutdown()

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
        container = QtWidgets.QHBoxLayout()
        container.setContentsMargins(5,5,5,5)
        container.addLayout(self.makeQRCode())
        container.addLayout(self.makeInfoPane())
        self.setLayout(container)
        self.setMinimumSize(self.sizeHint())

    def makeQRCode(self):
        image = qrcode.make(self.file.url, box_size=5, image_factory=qrcode.image.svg.SvgPathImage)
        widget = QtSvg.QSvgWidget()
        with BytesIO() as f:
            image.save(f)
            widget.load(f.getvalue())

        # Fix dark themes.
        pal = QtGui.QPalette(widget.palette())
        if pal.color(QtGui.QPalette.Window).getHsv()[2] < 200:
            pal.setColor(QtGui.QPalette.Window, QtGui.QColor("white"))
            widget.setPalette(pal)
            widget.setAutoFillBackground(True)

        container = QtWidgets.QHBoxLayout()
        widget.setMinimumSize(150, 150)
        container.setAlignment(QtCore.Qt.AlignCenter)
        container.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        container.addWidget(widget)
        return container

    def makeInfoPane(self):
        pane = QtWidgets.QVBoxLayout()
        pane.addLayout(self.makeUrlPane())
        pane.addWidget(self.makeTransfersPane())
        return pane

    def makeUrlPane(self):
        url = QtWidgets.QLabel(self.file.url)
        url.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse);
        url.setCursor(QtCore.Qt.IBeamCursor)
        copyLink = QtWidgets.QPushButton()
        copyLink.setIcon(QtGui.QIcon.fromTheme("edit-copy"))
        copyLink.clicked.connect(self.copyToClipboard)

        url_pane = QtWidgets.QHBoxLayout()
        url_pane.addWidget(url)
        url_pane.addStretch(1)
        url_pane.addWidget(copyLink)
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
        self.request.on("failure", sync(self.onFailure))

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

