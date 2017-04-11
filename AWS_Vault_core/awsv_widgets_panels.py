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
from AWS_Vault_core import awsv_config
reload(awsv_config)
from AWS_Vault_core import awsv_widgets_pathbar as pathbar
reload(pathbar)
from AWS_Vault_core import awsv_widgets_inputs
reload(awsv_widgets_inputs)

from AWS_Vault_core import awsv_connection

ICONS = os.path.dirname(__file__) + "\\icons\\"

exe = sys.executable.split(os.sep)[-1].split('.')[0]
if exe in ["hindie", "houdinicore", "hescape", "houdinifx"]:
    IS_HOUDINI = True
else:
    IS_HOUDINI = False

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

    def stop(self):
        self.movie.stop()

    def start(self):
        self.movie.start()

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

class PanelFileButtons(QtWidgets.QWidget):

    def __init__(self, parent):
        super(PanelFileButtons, self).__init__(parent=parent)

        self.panelfile = parent
        self.local_file_path = self.panelfile.local_file_path
        self.state_fetcher = None

        self.buttons_layout = QtWidgets.QHBoxLayout()

        self.activity = ActivityWidget()
        self.activity.setFixedHeight(26)
        self.buttons_layout.addWidget(self.activity)
        self.activity.stop()
        self.activity.setVisible(False)

        self.save_to_cloud_button = QtWidgets.QPushButton("")
        self.save_to_cloud_button.setStyleSheet("""QPushButton{background-color: transparent;border: 0px}
                                             QPushButton:hover{background-color: #607e9c;border: 0px}""")
        self.save_to_cloud_button.setIcon(QtGui.QIcon(ICONS + "cloud_save.png"))
        self.save_to_cloud_button.setIconSize(QtCore.QSize(26, 26))
        self.save_to_cloud_button.setFixedSize(QtCore.QSize(28, 28))
        self.save_to_cloud_button.setToolTip("Press this button to save the file to the cloud")
        self.save_to_cloud_button.clicked.connect(self.panelfile.save_to_cloud)
        self.buttons_layout.addWidget(self.save_to_cloud_button)

        self.is_on_cloud_button = QtWidgets.QPushButton("")
        self.is_on_cloud_button.setStyleSheet("""QPushButton{background-color: transparent;border: 0px}
                                             QPushButton:hover{background-color: #607e9c;border: 0px}""")
        if self.panelfile.state == awsv_objects.FileState.LOCAL_ONLY:
            self.is_on_cloud_button.setIcon(QtGui.QIcon(ICONS + "cloud_close.png"))
        else:
            self.is_on_cloud_button.setIcon(QtGui.QIcon(ICONS + "cloud_checkmark.png"))
            self.is_on_cloud_button.clicked.connect(self.panelfile.get_from_cloud)
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
        self.refresh_button.clicked.connect(self.refresh_state)
        self.buttons_layout.addWidget(self.refresh_button)

        self.setLayout(self.buttons_layout)

        self.refresh_state()

    def enable_buttons(self, toggle):

        self.save_to_cloud_button.setEnabled(toggle)
        self.is_on_cloud_button.setEnabled(toggle)
        self.lock_button.setEnabled(toggle)
        self.infos_button.setEnabled(toggle)
        self.refresh_button.setEnabled(toggle)

    def start_state_refreshgin(self):

        self.activity.start()
        self.activity.setVisible(True)

        self.save_to_cloud_button.setVisible(False)
        self.is_on_cloud_button.setVisible(False)
        self.lock_button.setVisible(False)
        self.infos_button.setVisible(False)
        self.refresh_button.setVisible(False)

    def end_state_refreshing(self, state):

        self.activity.stop()
        self.activity.setVisible(False)

        if state == awsv_objects.FileState.CLOUD_ONLY:
            self.is_on_cloud_button.setIcon(QtGui.QIcon(ICONS + "cloud_only.png"))
        elif state == awsv_objects.FileState.LOCAL_ONLY:
            self.is_on_cloud_button.setIcon(QtGui.QIcon(ICONS + "cloud_close.png"))
        else:
            self.is_on_cloud_button.setIcon(QtGui.QIcon(ICONS + "cloud_checkmark.png"))

        self.save_to_cloud_button.setVisible(True)
        self.is_on_cloud_button.setVisible(True)
        self.lock_button.setVisible(True)
        self.infos_button.setVisible(True)
        self.refresh_button.setVisible(True)

        self.state_fetcher = None

    def refresh_state(self):
        
        if self.state_fetcher is not None:
            self.state_fetcher.terminate()

        self.state_fetcher = awsv_io.FetchStateThread(self.local_file_path)
        self.state_fetcher.end_sgn.connect(self.end_state_refreshing)
        self.state_fetcher.start_sgn.connect(self.start_state_refreshgin)
        self.state_fetcher.start()

class PanelFile(PanelFolder):

    def __init__(self, name="", path="", state=awsv_objects.FileState.NONE, parent=None):

        self.state = state
        root = awsv_connection.CURRENT_BUCKET["local_root"] + '/'
        self.local_file_path = root + path
        if os.path.exists(self.local_file_path):
            self.local_file_size = os.path.getsize(self.local_file_path) * 0.000001
        else:
            self.local_file_size = 0.0
        self.worker = None

        super(PanelFile, self).__init__(name=name, path=path, parent=parent)

        self.setToolTip("Local path: " + self.local_file_path + '\n' + \
                        "Cloud path: " + path + '\n' + \
                        "File Size: " + '{0:.2f}'.format(self.local_file_size) + " mb")

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

        self.file_buttons = PanelFileButtons(self)
        self.buttons_layout.addWidget(self.file_buttons)

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
        self.file_buttons.enable_buttons(False)

    def end_progress(self, mode):

        if mode == 0:
            self.upload_movie.stop()
            self.activity_upload_ico.setVisible(False)
        else:
            self.activity_download_ico.setVisible(False)
            self.download_movie.stop()

        self.activity_progress.setValue(0)
        self.activity_progress.setVisible(False)
        self.file_buttons.enable_buttons(True)

        ico = QtGui.QIcon(ICONS + "cloud_checkmark.png")
        self.file_buttons.is_on_cloud_button.setIcon(ico)

    def get_from_cloud(self):

        if not os.path.exists(self.local_file_path):
            confirm_msg = "Get file " + self.local_file_path.split('/')[-1] + " from cloud ?"
            ico = QtWidgets.QMessageBox.Information
        else:
            confirm_msg = ("Get file " + self.local_file_path + " from cloud ?\n"
                           "Warning: This will erase your local modification")
            ico = QtWidgets.QMessageBox.Warning

        ask = QtWidgets.QMessageBox(ico, "Confirm", confirm_msg,
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
            QtWidgets.QMessageBox.critical(self, "Error", "File not found: " + self.local_file_path)
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
        
        ask_msg = awsv_widgets_inputs.MessageInput(parent=self)
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