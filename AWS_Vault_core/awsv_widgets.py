import os
import sys
import datetime
import time
import tempfile

from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtCore

from AWS_Vault_core import awsv_io
reload(awsv_io)
from AWS_Vault_core import awsv_objects
reload(awsv_objects)
from AWS_Vault_core import awsv_connection

ICONS = os.path.dirname(__file__) + "\\icons\\"

exe = sys.executable.split(os.sep)[-1].split('.')[0]
if exe in ["hindie", "houdinicore", "hescape", "houdinifx"]:
    IS_HOUDINI = True
else:
    IS_HOUDINI = False

class ProjectSelector(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(ProjectSelector, self).__init__(parent=parent)
        
        self.main_ui = parent
        
        main_layout = QtWidgets.QVBoxLayout()
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        main_layout.setAlignment(QtCore.Qt.AlignCenter)
        
        self.open_project_button = QtWidgets.QPushButton(" Open a root folder")
        self.open_project_button.setIconSize(QtCore.QSize(64, 64))
        self.open_project_button.setIcon(QtGui.QIcon(ICONS + "folder_open.svg"))
        self.open_project_button.clicked.connect(self.main_ui.init_root)
        self.open_project_button.setFlat(True)
        self.open_project_button.setStyleSheet("""QPushButton{background-color: transparent}
                                                  QPushButton:hover{background-color: rgba(90, 90, 185, 80)}""")
        self.open_project_button.setContentsMargins(10,10,10,10)
        main_layout.addWidget(self.open_project_button)

        self.history_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(self.history_layout)

        self.setLayout(main_layout)

        self.init_history()

    def init_history(self):

        history = tempfile.gettempdir() + os.sep + "aws_vault_projects"
        if not os.path.exists(history): return

        with open(history, 'r') as f:
            history_files = [n.replace('\n', '') for n in f.readlines()]

        for history_path in history_files:
            if not os.path.exists(history_path):
                continue

            history_path = history_path.replace('\\', '/')
            btn = QtWidgets.QPushButton(history_path)
            btn.setStyleSheet("""QPushButton{background-color: transparent;
                                             color: #a2a4b4;
                                             border: 0px}
                                 QPushButton:hover{color: #c4c6d7}""")
            btn.clicked.connect(lambda v=history_path: self.init_root_from_history(v))
            self.history_layout.addWidget(btn)

    def init_root_from_history(self, path):

        self.main_ui.init_root(path)

class ActivityWidget(QtWidgets.QWidget):

    def __init__(self, *args):
        super(ActivityWidget, self).__init__(*args)

        self.main_layout = QtWidgets.QVBoxLayout()

        self.movie = QtGui.QMovie(ICONS + "loading.gif", parent=self)

        self.movie_screen = QtWidgets.QLabel()
        self.movie_screen.setSizePolicy(QtWidgets.QSizePolicy.Expanding, 
                                        QtWidgets.QSizePolicy.Expanding)        
        self.movie_screen.setAlignment(QtCore.Qt.AlignCenter)
        self.movie_screen.setMovie(self.movie)
        
        self.main_layout.addWidget(self.movie_screen)
        self.setLayout(self.main_layout)
        self.movie.start()

class MessageInput(QtWidgets.QDialog):

    def __init__(self, is_mandatory=False, parent=None):
        super(MessageInput, self).__init__(parent=parent)

        self.setWindowTitle("Message")
        self.message = ""

        main_layout = QtWidgets.QVBoxLayout()
        if is_mandatory:
            msg = "Enter a message ( mantadory ):"
        else:
            msg = "Enter a message:"
        self.lbl = QtWidgets.QLabel(msg)
        main_layout.addWidget(self.lbl)

        self.text_edit = QtWidgets.QTextEdit()
        main_layout.addWidget(self.text_edit)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.valid_btn = QtWidgets.QPushButton("Ok")
        self.valid_btn.clicked.connect(self.valid)
        self.close_btn = QtWidgets.QPushButton("Cancel")
        self.close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(self.valid_btn)
        buttons_layout.addWidget(self.close_btn)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

        self.is_mandatory = is_mandatory

        self.setStyleSheet("""QLabel{background-color: transparent}
                              QTextEdit{background-color: #1a1a1a;
                                        color: #f2f2f2}""")

    def valid(self):

        msg = self.text_edit.toPlainText()
        if msg.replace(' ', '') == "" and self.is_mandatory:
            QtWidgets.QMessageBox.warning(self, "Warning", "Message is empty")
            return

        self.message = msg
        self.close()

class PathBarDelimiter(QtWidgets.QLabel):

    def __init__(self, parent=None):
        super(PathBarDelimiter, self).__init__(parent=parent)

        self.setFixedHeight(24)
        self.setFixedWidth(24)
        self.setContentsMargins(0,0,0,0)
        self.setPixmap(QtGui.QIcon(ICONS + "pathbar_delimiter.png").pixmap(22,22))
        self.setStyleSheet("""QFrame{background-color: transparent;
                                     border: 0px solid black}""")

class PathBarButton(QtWidgets.QPushButton):

    def __init__(self, label="", icon="folder.svg", path="", isroot=False, parent=None):
        super(PathBarButton, self).__init__(parent=parent)

        self.isroot = isroot
        self.pathbar = parent
        self.setProperty("houdiniStyle", IS_HOUDINI)
        self.setStyleSheet("""QPushButton{background-color: transparent;
                                          border: 0px;
                                          padding: 2px}
                              QPushButton:hover{background-color: #444444;
                                                border: 0px;
                                                padding: 2px}""")
        self.setText(label)
        self.label = label
        self.path = path
        self.setToolTip(path)
        if icon != "":
            self.setIcon(QtGui.QIcon(ICONS + icon))
            self.setIconSize(QtCore.QSize(22,22))
        self.setFixedHeight(24)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self.setContentsMargins(0,0,0,0)
        self.clicked.connect(self.goto)

    def goto(self):

        main_ui = self.pathbar.main_ui
        if not self.isroot:
            bucket_name = awsv_connection.CURRENT_BUCKET["name"]
            r = self.path.replace(bucket_name + '/', '')
            main_ui.show_panel(panel_name=self.label, panel_path=r, data=None)
        else:
             self.pathbar.reset()
             main_ui.back_to_root()

class PathBar(QtWidgets.QFrame):

    def __init__(self, root="", parent=None):
        super(PathBar, self).__init__(parent=parent)

        self.setProperty("houdiniStyle", IS_HOUDINI)
        self.setObjectName("pathbar")
        self.main_ui = parent
        self.root = root
        self.setStyleSheet("""QFrame{
                                 background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                             stop: 0 #3d3d3d, stop: 1.0 #303030);
                                 border: 1px solid #232425}""")
        self.setFixedHeight(32)
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QHBoxLayout()
        self.scroll_layout.setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.scroll_layout.setSpacing(0)
        self.scroll_layout.setContentsMargins(0,0,0,0)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setContentsMargins(0,0,0,0)
        self.scroll_area.setStyleSheet("""QScrollArea{background-color: transparent;
                                                      border: 0px}
                                          QScrollBar{height: 8px}""")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_widget)

        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.setContentsMargins(5,0,0,0)
        self.main_layout.addWidget(self.scroll_area)

        self.root_w = PathBarButton(label=root, icon="root.svg", path=root, isroot=True, parent=self)
        self.scroll_layout.addWidget(self.root_w)
        self.scroll_layout.addWidget(PathBarDelimiter())

        self.setLayout(self.main_layout)

    def reset(self):

        for i in range(self.scroll_layout.count())[::-1]:
            it = self.scroll_layout.itemAt(i)
            
            w = it.widget()
            if isinstance(w, PathBarButton) and w.label == self.root:                
                continue

            self.scroll_layout.removeWidget(w)
            w.setParent(None)
            w.deleteLater()
            self.scroll_layout.update()
        
        self.scroll_layout.addWidget(PathBarDelimiter())

    def set_current_level(self, folder_path):

        levels = [n for n in folder_path.split('/') if n != ""]

        for i in range(self.scroll_layout.count())[::-1]:
            it = self.scroll_layout.itemAt(i)
            
            w = it.widget()
            if isinstance(w, PathBarButton) and w.label == self.root:                
                continue

            self.scroll_layout.removeWidget(w)
            w.setParent(None)
            w.deleteLater()
            self.scroll_layout.update()
        
        self.scroll_layout.addWidget(PathBarDelimiter())

        _path = self.root
        for level in levels:
            _path += '/' + level
            el = PathBarButton(label=level, icon="folder.svg", path=_path + '/', parent=self)
            self.scroll_layout.addWidget(el)
            self.scroll_layout.addWidget(PathBarDelimiter())

        self.scroll_layout.update()

class PanelFolder(QtWidgets.QFrame):

    def __init__(self, name="", path="", parent=None):
        super(PanelFolder, self).__init__(parent=parent)

        self.panel = parent

        self.path = path
        self.name = name

        self.setToolTip("Path: " + str(self.path))

        self.setAutoFillBackground(True)
        self.setStyleSheet("""QFrame{background-color: #3b4753}
                              QFrame:hover{background-color: #4c5967}""")
        self.setFixedHeight(45)
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setSpacing(5)
        self.main_layout.setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignHCenter)
        self.ico = QtWidgets.QLabel("")
        self.ico.setFixedHeight(22)
        self.ico.setStyleSheet("background-color: transparent")
        self.ico.setPixmap(QtGui.QIcon(ICONS + "folder.svg").pixmap(28, 28))
        self.main_layout.addWidget(self.ico)
        self.label = QtWidgets.QLabel(name)
        self.label.setStyleSheet("background-color: transparent")
        self.main_layout.addWidget(self.label)
        self.setLayout(self.main_layout)
        self.setContentsMargins(15,0,0,0)
        self.init_buttons()

    def init_buttons(self):
        return

    def mouseDoubleClickEvent(self, event):

        main_ui = self.panel.main_ui
        bucket = awsv_connection.CURRENT_BUCKET["bucket"]
        data = awsv_io.get_bucket_folder_elements(folder_name=self.path)
        main_ui.show_panel(panel_name=self.name, panel_path=self.path, data=data)

class PanelFile(PanelFolder):

    def __init__(self, name="", path="", state=awsv_objects.FileState.NONE, parent=None):
        self.state = state
        super(PanelFile, self).__init__(name=name, path=path, parent=parent)

        root = awsv_connection.CURRENT_BUCKET["local_root"] + '/'
        self.local_file_path = root + self.path
        self.local_file_size = os.path.getsize(self.local_file_path) * 0.000001
        
        self.setToolTip("Local path: " + self.local_file_path + '\n' + \
                        "Cloud path: " + self.path + '\n' + \
                        "File Size: " + '{0:.2f}'.format(self.local_file_size) + " mb")
        
        self.worker = None

    def init_buttons(self):
        
        self.setStyleSheet("""QFrame{background-color: #3e5975}
                              QFrame:hover{background-color: #4d6b89}""")

        file_extension = self.path.split('.')[-1]
        icon = ICONS + "file_types/" + file_extension + ".svg"
        if not os.path.exists(icon):
            self.ico.setPixmap(QtGui.QIcon(ICONS + "document.svg").pixmap(28, 28))
        else:
            self.ico.setPixmap(QtGui.QIcon(icon).pixmap(28, 28))
        
        self.activity_progress = QtWidgets.QProgressBar()
        self.activity_progress.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                             QtWidgets.QSizePolicy.Minimum)
        self.activity_progress.setVisible(False)
        self.activity_progress.setStyleSheet("""QProgressBar {
                                                border: 0px;
                                                color: #cbcbcb;
                                 background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                             stop: 0 #3d3d3d, stop: 1.0 #303030);}
                                              QProgressBar::chunk {
                                 background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                             stop: 0 #437db9, stop: 1.0 #4b89ca);
                                                width: 20px;}""")
        self.main_layout.addWidget(self.activity_progress)

        self.activity_upload_ico = QtWidgets.QLabel()
        self.activity_upload_ico.setFixedHeight(29)
        self.activity_upload_ico.setFixedWidth(29)
        self.upload_movie = QtGui.QMovie(ICONS + "upload.gif", parent=self)
        self.activity_upload_ico.setMovie(self.upload_movie)
        self.activity_upload_ico.setVisible(False)
        self.main_layout.addWidget(self.activity_upload_ico)

        self.activity_download_ico = QtWidgets.QLabel()
        self.activity_download_ico.setFixedHeight(29)
        self.activity_download_ico.setFixedWidth(29)
        self.download_movie = QtGui.QMovie(ICONS + "download.gif", parent=self)
        self.activity_download_ico.setMovie(self.download_movie)
        self.activity_download_ico.setVisible(False)
        self.main_layout.addWidget(self.activity_download_ico)

        self.buttons_layout = QtWidgets.QHBoxLayout()
        self.buttons_layout.addStretch(1)
        self.buttons_layout.setAlignment(QtCore.Qt.AlignRight)

        self.save_to_cloud_button = QtWidgets.QPushButton("")
        self.save_to_cloud_button.setStyleSheet("""QPushButton{background-color: transparent;border: 0px}
                                             QPushButton:hover{background-color: #607e9c;border: 0px}""")
        self.save_to_cloud_button.setIcon(QtGui.QIcon(ICONS + "cloud_save.png"))
        self.save_to_cloud_button.setIconSize(QtCore.QSize(26, 26))
        self.save_to_cloud_button.setFixedSize(QtCore.QSize(28, 28))
        self.save_to_cloud_button.setToolTip("Press this button to save the file to the cloud")
        self.save_to_cloud_button.clicked.connect(self.save_to_cloud)
        self.buttons_layout.addWidget(self.save_to_cloud_button)

        self.is_on_cloud_button = QtWidgets.QPushButton("")
        self.is_on_cloud_button.setStyleSheet("""QPushButton{background-color: transparent;border: 0px}
                                             QPushButton:hover{background-color: #607e9c;border: 0px}""")
        if self.state == awsv_objects.FileState.LOCAL_ONLY:
            self.is_on_cloud_button.setIcon(QtGui.QIcon(ICONS + "cloud_close.png"))
        else:
            self.is_on_cloud_button.setIcon(QtGui.QIcon(ICONS + "cloud_checkmark.png"))
            self.is_on_cloud_button.clicked.connect(self.get_from_cloud)
        self.is_on_cloud_button.setIconSize(QtCore.QSize(26, 26))
        self.is_on_cloud_button.setFixedSize(QtCore.QSize(28, 28))
        self.buttons_layout.addWidget(self.is_on_cloud_button)

        self.lock_button = QtWidgets.QPushButton("")
        self.lock_button.setStyleSheet("""QPushButton{background-color: transparent;border: 0px}
                                             QPushButton:hover{background-color: #607e9c;border: 0px}""")
        self.lock_button.setIcon(QtGui.QIcon(ICONS + "notlock.png"))
        self.lock_button.setIconSize(QtCore.QSize(26, 26))
        self.lock_button.setFixedSize(QtCore.QSize(28, 28))
        self.buttons_layout.addWidget(self.lock_button)

        self.infos_button = QtWidgets.QPushButton("")
        self.infos_button.setStyleSheet("""QPushButton{background-color: transparent;border: 0px}
                                             QPushButton:hover{background-color: #607e9c;border: 0px}""")
        self.infos_button.setIcon(QtGui.QIcon(ICONS + "info.svg"))
        self.infos_button.setIconSize(QtCore.QSize(26, 26))
        self.infos_button.setFixedSize(QtCore.QSize(28, 28))
        self.buttons_layout.addWidget(self.infos_button)

        self.refresh_button = QtWidgets.QPushButton("")
        self.refresh_button.setIconSize(QtCore.QSize(26, 26))
        self.refresh_button.setFixedSize(QtCore.QSize(28, 28))
        self.refresh_button.setStyleSheet("""QPushButton{background-color: transparent;border: 0px}
                                             QPushButton:hover{background-color: #607e9c;border: 0px}""")
        self.refresh_button.setToolTip("Refresh current file metadata")
        self.refresh_button.setIcon(QtGui.QIcon(ICONS + "reload.svg"))
        self.buttons_layout.addWidget(self.refresh_button)

        self.main_layout.addLayout(self.buttons_layout)

    def refresh_state(self):

        return

    def update_progress(self, progress):
        
        next_val = self.activity_progress.value() + progress
        self.activity_progress.setValue(next_val)

    def start_progress(self, mode):

        if mode == 0:
            s = os.path.getsize(self.local_file_path)
            self.activity_progress.setMaximum(s)
            self.activity_upload_ico.setVisible(True)
            self.upload_movie.start()
        else:
            s = awsv_io.get_object_size(self.local_file_path)
            self.activity_progress.setMaximum(s)
            self.activity_download_ico.setVisible(True)
            self.download_movie.start()

        self.activity_progress.setValue(0)
        self.activity_progress.setVisible(True)
        self.save_to_cloud_button.setEnabled(False)
        self.lock_button.setEnabled(False)
        self.infos_button.setEnabled(False)
        self.is_on_cloud_button.setEnabled(False)
        self.refresh_button.setEnabled(False)

    def end_progress(self, mode):

        if mode == 0:
            self.upload_movie.stop()
            self.activity_upload_ico.setVisible(False)
        else:
            self.activity_download_ico.setVisible(False)
            self.download_movie.stop()

        self.activity_progress.setValue(0)
        self.activity_progress.setVisible(False)
        self.save_to_cloud_button.setEnabled(True)
        self.lock_button.setEnabled(True)
        self.infos_button.setEnabled(True)
        self.is_on_cloud_button.setEnabled(True)
        self.refresh_button.setEnabled(True)

        self.is_on_cloud_button.setIcon(QtGui.QIcon(ICONS + "cloud_checkmark.png"))

    def get_from_cloud(self):

        if not os.path.exists(self.local_file_path):
            QtWidgets.QMessageBox.critical(self, "Error", "File not found: " + file_path)
            return

        confirm_msg = ("Get file " + self.local_file_path + " from cloud ?\n"
                       "Warning: This will erase your local modification")
        ask = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Confirm", confirm_msg,
                                    buttons = QtWidgets.QMessageBox.StandardButton.Yes|\
                                              QtWidgets.QMessageBox.StandardButton.No,
                                    parent=self)
        geo = ask.frameGeometry()
        
        ask.move(QtGui.QCursor.pos() - ( geo.topRight() * 3 ))
        ask.setStyleSheet("""QMessageBox{background-color: #3e5975}
                             QFrame{background-color: #3e5975}
                             QLabel{background-color: #3e5975}""")
        
        if ask.exec_() == QtWidgets.QMessageBox.StandardButton.No: return

        self.activity_progress.setVisible(True)

        self.worker = awsv_io.FileIOThread(self.local_file_path, mode=1)
       
        self.worker.start_sgn.connect(self.start_progress)
        self.worker.end_sgn.connect(self.end_progress)
        self.worker.update_progress_sgn.connect(self.update_progress)

        self.worker.start()

    def save_to_cloud(self):

        if not os.path.exists(self.local_file_path):
            QtWidgets.QMessageBox.critical(self, "Error", "File not found: " + file_path)
            return
        
        confirm_msg = "Send file: {0} on the cloud ?\nSize: {1:.2f} Mb".format(self.local_file_path,
                                                                         self.local_file_size)
        ask = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, "Confirm", confirm_msg,
                                    buttons = QtWidgets.QMessageBox.StandardButton.Yes|\
                                              QtWidgets.QMessageBox.StandardButton.No,
                                    parent=self)
        geo = ask.frameGeometry()
        
        ask.move(QtGui.QCursor.pos() - ( geo.topRight() * 3 ))
        ask.setStyleSheet("""QMessageBox{background-color: #3e5975}
                             QFrame{background-color: #3e5975}
                             QLabel{background-color: #3e5975}""")
        
        if ask.exec_() == QtWidgets.QMessageBox.StandardButton.No: return
        
        ask_msg = MessageInput(parent=self)
        ask_msg.move(QtGui.QCursor.pos() - ( geo.topRight() * 3 ))
        ask_msg.exec_()
        msg = ask_msg.message

        self.activity_progress.setVisible(True)

        s = os.path.getsize(self.local_file_path)
        self.activity_progress.setMaximum(s)

        self.worker = awsv_io.FileIOThread(self.local_file_path, message=msg)
       
        self.worker.start_sgn.connect(self.start_progress)
        self.worker.end_sgn.connect(self.end_progress)
        self.worker.update_progress_sgn.connect(self.update_progress)

        self.worker.start()

class Panel(QtWidgets.QFrame):

    def __init__(self, panel_name="", panel_folder_path="", subfolder="", parent=None):
        super(Panel, self).__init__(parent=parent)

        self.main_ui = parent

        self.subfolder = subfolder
        self.fetcher = None
        
        self.setProperty("houdiniStyle", IS_HOUDINI)
        self.setObjectName("panel_" + panel_name)
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        # panel header
        self.header_layout = QtWidgets.QHBoxLayout()
        self.header = QtWidgets.QFrame()
        self.header.setAutoFillBackground(True)
        self.header.setObjectName("header")
        self.ico = QtWidgets.QLabel("")
        self.ico.setFixedHeight(22)
        self.ico.setStyleSheet("background-color: transparent")
        self.ico.setPixmap(QtGui.QIcon(ICONS + "folder_open.svg").pixmap(28, 28))
        self.header_layout.addWidget(self.ico)
        self.header_layout.addWidget(QtWidgets.QLabel(panel_name.split('/')[-1]))
        self.header_layout.addStretch(1)
        self.refresh_button = QtWidgets.QPushButton("")
        self.refresh_button.setFixedHeight(28)
        self.refresh_button.setFixedWidth(28)
        self.refresh_button.setIconSize(QtCore.QSize(26, 26))
        self.refresh_button.setStyleSheet("""QPushButton{background-color: transparent;border: 0px}
                                             QPushButton:hover{background-color: #525666;border: 0px}""")
        self.refresh_button.clicked.connect(lambda: self.init_fetching(reset=True))
        self.refresh_button.setToolTip("Refresh current folder state")
        self.refresh_button.setIcon(QtGui.QIcon(ICONS + "reload.svg"))
        self.header_layout.addWidget(self.refresh_button)
        self.header.setLayout(self.header_layout)
        self.main_layout.addWidget(self.header)
        self.header.setStyleSheet("""QFrame{background-color: #2e3241}""")

        # acticity monitor
        self.activity_w = ActivityWidget()
        self.main_layout.addWidget(self.activity_w)

        # elements
        self.elements = []
        self.element_scroll = QtWidgets.QScrollArea()
        self.element_scroll.setStyleSheet("""QScrollArea{background-color: transparent;
                                                         border: 0px}""")
        self.element_scroll.setWidgetResizable(True)
        self.elements_layout = QtWidgets.QVBoxLayout()
        self.elements_layout.setAlignment(QtCore.Qt.AlignTop)
        self.elements_layout.setSpacing(0)
        self.elements_layout.setContentsMargins(0,0,0,0)
        self.elements_widget = QtWidgets.QWidget()
        self.elements_widget.setLayout(self.elements_layout)
        self.element_scroll.setWidget(self.elements_widget)

        self.main_layout.addWidget(self.element_scroll)
        
        self.setLayout(self.main_layout)
        
        self.init_fetching()

    def init_fetching(self, reset=False):

        if reset:
            for w in self.elements:
                self.elements_layout.removeWidget(w)
                w.setParent(None)
                w.deleteLater()
            self.elements = []

        self.elements_layout.update()

        self.activity_w.setVisible(True)

        if self.fetcher is not None:
            self.fetcher.cancel = True
            self.fetcher.wait(2)
            self.fetcher = None
            time.sleep(1)

        self.fetcher = awsv_io.ElementFetcher()
        self.fetcher.bucket = awsv_connection.CURRENT_BUCKET["bucket"]
        self.fetcher.folder_name = self.subfolder
        self.fetcher.end.connect(self.element_fetched)
        self.fetcher.start()

    def element_fetched(self, data):

        if data is None: return

        self.fetcher.wait(1)
        self.fetcher = None

        cloud_data = data[0]
        local_data = data[1]
        
        # append folders
        for f in sorted(cloud_data.folders):
            folder_name = f.split('/')[-1]
            w = PanelFolder(name=folder_name, path=f+'/', parent=self)
            self.elements.append(w)
            self.elements_layout.addWidget(w)

        for f in sorted(local_data.folders):
            if f in cloud_data.folders: continue
            folder_name = f.split('/')[-1]
            w = PanelFolder(name=folder_name, path=f+'/', parent=self)
            self.elements.append(w)
            self.elements_layout.addWidget(w)

        # append TODO: metadata in FolderFile class
        for f in sorted(cloud_data.files):
            file_name = f.split('/')[-1]
            w = PanelFile(name=file_name, path=f, parent=self)
            self.elements.append(w)
            self.elements_layout.addWidget(w)

        for f in sorted(local_data.files):
            if f in cloud_data.files: continue
            file_name = f.split('/')[-1]
            w = PanelFile(name=file_name, path=f, state=awsv_objects.FileState.LOCAL_ONLY,
                          parent=self)
            self.elements.append(w)
            self.elements_layout.addWidget(w)
        
        self.activity_w.setVisible(False)

class MainWidget(QtWidgets.QFrame):

    def __init__(self, parent=None):
        super(MainWidget, self).__init__(parent=parent)

        self.setProperty("houdiniStyle", IS_HOUDINI)

        self.pathbar = None
        self.panels = {}
        self.cur_panel = None
        self.root_panel = None

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(1,1,1,1)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.main_menu = QtWidgets.QMenuBar(self)
        self.main_menu.setFixedHeight(25)
        self.file_menu = self.main_menu.addMenu("File")
        self.open_root_act = QtWidgets.QAction("Open Root Folder", self)
        self.close_root_act = QtWidgets.QAction("Close Current Root", self)
        self.file_menu.addAction(self.open_root_act)
        self.file_menu.addAction(self.close_root_act)
        
        self.main_layout.addWidget(self.main_menu)

        self.init_button = ProjectSelector(self)
        self.main_layout.addWidget(self.init_button)

        self.setLayout(self.main_layout)

    def back_to_root(self):

        if self.cur_panel:
            self.cur_panel.setVisible(False)

        if self.root_panel:
            self.root_panel.setVisible(True)
        self.cur_panel = self.root_panel

    def show_panel(self, panel_name="", panel_path="", data=None):
        """ Add a panel according to given cloud's folder data aka
            => BucketFolderElements
        """
        if self.cur_panel:
            self.cur_panel.setVisible(False)
        self.main_layout.update()

        bucket_name = awsv_connection.CURRENT_BUCKET["name"]
        panel_id = bucket_name + '/' + panel_path

        panel = self.panels.get(panel_id)
        if panel:
            panel.setVisible(True)
        
        else:
            
            panel = Panel(panel_name, panel_path, subfolder=panel_path, parent=self)
            self.main_layout.addWidget(panel)
            self.panels[panel_id] = panel

        self.cur_panel = panel
        self.pathbar.set_current_level(panel_path)

    def init_root(self, root=""):
        
        if not root:
            r = QtWidgets.QFileDialog.getExistingDirectory(self, "Pick a root folder")
            if not r: return

            root = r.replace('\\', '/')
        bucket_name = root.split('/')[-1]
        awsv_connection.init_connection()

        bucket = awsv_io.get_bucket(bucket_name)
        if not bucket:
            QtWidgets.QMessageBox.critical(self, "Error", "Can't open root: {}.\nDoes the folder exist on the cloud ?".format(root))
            return False

        awsv_connection.CONNECTIONS["root"] = root + '/'
        awsv_connection.CURRENT_BUCKET = {"name" : bucket_name,
                                          "bucket" : bucket,
                                          "local_root" : root,
                                          "connection_time" : datetime.datetime.now()}
        self.init_button.setVisible(False)

        self.pathbar = PathBar(root = bucket_name, parent=self)
        self.main_layout.addWidget(self.pathbar)
        
        p = Panel(bucket_name, root, subfolder="", parent=self)
        self.panels[bucket_name + '/'] = p
        self.main_layout.addWidget(p)
        self.cur_panel = p
        self.root_panel = p

        # add to history
        history = tempfile.gettempdir() + os.sep + "aws_vault_projects"
        if not os.path.exists(history):
            with open(history, 'w') as f:
                f.write(root + '\n')
        else:
            with open(history, 'r') as f:
                history = f.readlines()

            if root + '\n' in history:
                return

            if len(history) > 10:
                history.pop(0)
                history.append(root + '\n')
                with open(history, 'w') as f:
                    f.writelines(history)
            else:
                with open(history, 'a') as f:
                    f.write(root + '\n')


    def closeEvent(self, event):
        
        for panel in self.panels.itervalues():
            
            panel.bucket = None
            if panel.fetcher is not None:
                panel.fetcher.terminate()

        super(MainWidget, self).closeEvent(event)