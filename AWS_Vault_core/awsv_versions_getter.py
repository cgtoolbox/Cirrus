import sys
import os
from AWS_Vault_core.awsv_logger import Logger

from PySide2 import QtGui
from PySide2 import QtCore
from PySide2 import QtWidgets

from AWS_Vault_core import awsv_io
reload(awsv_io)

import botocore

ICONS = os.path.dirname(__file__) + "\\icons\\"

class VersionPickerThread(QtCore.QThread):

    start_sgn = QtCore.Signal()
    append_version_sgn = QtCore.Signal(object, int, bool, str, bool, str, str)  # latest datetime, size, is_latest, version_id, delete_marker
    end_sgn = QtCore.Signal(int)

    def __init__(self, object_path):
        super(VersionPickerThread, self).__init__()

        self.object_path = object_path
        self.cancel = False

    def run(self):

        self.start_sgn.emit()
        n_ver = 0
        Logger.Log.debug("Fetchin version infos for object: " + self.object_path)

        version = awsv_io.get_object_versions(self.object_path)

        for v in version:

            if self.cancel:
                self.end_sgn.emit(n_ver)

            latest = v.last_modified
            _size = v.size
            is_latest = v.is_latest
            v_id = v.version_id

            message = "None"
            user = "None"
            delete_marker = False
            try:
                if self.cancel:
                    self.end_sgn.emit(n_ver)
                head = v.head()
            except botocore.exceptions.ClientError as e:
                head = None

            if head:
                delete_marker = head.get("DeleteMarker", False)

                if self.cancel:
                    self.end_sgn.emit(n_ver)

                meta = head.get("Metadata")
                if meta:
                    message = meta.get("upload_message", "None")
                    user = meta.get("submit_user", "None")

            self.append_version_sgn.emit(latest, _size, is_latest, v_id,
                                         delete_marker, message, user)
            n_ver += 0

        self.end_sgn.emit(n_ver)


class VersionPicker(QtWidgets.QDialog):

    def __init__(self, object_path, parent=None):
        super(VersionPicker, self).__init__(parent=parent)

        self.setWindowFlags(QtCore.Qt.Tool)
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.setObjectName("versionPicker")
        self.setWindowTitle("Version Picker")

        self.object_path = object_path
        self.version_selected = None

        if not os.path.exists(object_path):
            main_layout.addWidget(QtWidgets.QLabel("Error, path not valid:" + object_path))
            self.setLayout(main_layout)
            return

        main_layout.addWidget(QtWidgets.QLabel(object_path))
        self.elements_progress = QtWidgets.QProgressBar()
        self.elements_progress.setTextVisible(False)
        self.elements_progress.setFixedHeight(10)
        self.elements_progress.setStyleSheet("""QProgressBar {
                                                border: 1px solid black;
                                                color: #cbcbcb;
                                 background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                             stop: 0 #3d3d3d, stop: 1.0 #303030);}
                                              QProgressBar::chunk {
                                 background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                             stop: 0 #437db9, stop: 1.0 #4b89ca);
                                                width: 20px;}""")
        main_layout.addWidget(self.elements_progress)

        self.n_items = 0
        self.table = QtWidgets.QTableWidget()
        self.table.setObjectName("versionTable")
        self.table.setStyleSheet("""QTableCornerButton::section {background: transparent;}""")
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Last Modified", "Comment", "Size", "Get"])
        main_layout.addWidget(self.table)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.close_and_cancel)
        main_layout.addWidget(close_btn)

        self.setLayout(main_layout)

        self.worker = VersionPickerThread(object_path)
        self.worker.start_sgn.connect(self.start_sgn)
        self.worker.end_sgn.connect(self.end_sgn)
        self.worker.append_version_sgn.connect(self.append_version)
        self.worker.start()

    def close_and_cancel(self):

        self.worker.cancel = True
        self.close()

    def end_sgn(self):

        self.elements_progress.setMinimum(0)
        self.elements_progress.setMaximum(1)
        self.elements_progress.setValue(1)

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    def start_sgn(self):

        self.elements_progress.setMinimum(0)
        self.elements_progress.setMaximum(0)

    def download_version(self, version_id):
        
        self.worker.cancel = True
        self.version_selected = version_id
        self.close()

    def append_version(self, date, size, is_latest, version_id,
                       delete_marker, message, user):

        self.table.setRowCount(self.n_items + 1)

        # latest
        time_lbl = QtWidgets.QLabel(str(date.ctime()))
        time_lbl.setContentsMargins(2,2,2,2)
        time_lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.table.setCellWidget(self.n_items, 0, time_lbl)

        # comment
        if message != "None":
            message = message + '\n(user: ' + user + ")"
        msg_lbl = QtWidgets.QLabel(message)
        msg_lbl.setContentsMargins(2,2,2,2)
        msg_lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.table.setCellWidget(self.n_items, 1, msg_lbl)

        # Size
        s = '{0:.3f} Mb'.format(size * 0.000001)
        size_lbl = QtWidgets.QLabel(s)
        size_lbl.setContentsMargins(2,2,2,2)
        size_lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.table.setCellWidget(self.n_items, 2, size_lbl)

        # get
        get_btn = QtWidgets.QPushButton("")
        get_btn.setFlat(True)
        get_btn.setStyleSheet("""QPushButton{background: transparent}""")
        get_btn.setIcon(QtGui.QIcon(ICONS + "download.svg"))
        
        
        get_btn.setIconSize(QtCore.QSize(26,26))
        get_btn.clicked.connect(lambda v=version_id: self.download_version(v))
        self.table.setCellWidget(self.n_items, 3, get_btn)

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.n_items += 1