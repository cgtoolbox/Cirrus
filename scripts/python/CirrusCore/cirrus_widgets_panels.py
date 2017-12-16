import os
import sys
import time
from CirrusCore.cirrus_logger import Logger

from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtCore

from CirrusCore import cirrus_io
reload(cirrus_io)
from CirrusCore import cirrus_versions_getter
reload(cirrus_versions_getter)
from CirrusCore import cirrus_threading
reload(cirrus_threading)
from CirrusCore import cirrus_objects
reload(cirrus_objects)
from CirrusCore import cirrus_widgets_pathbar as pathbar
reload(pathbar)
from CirrusCore import cirrus_widgets_inputs
reload(cirrus_widgets_inputs)
from CirrusCore import cirrus_plugin_parser
reload(cirrus_plugin_parser)
from CirrusCore.cirrus_connection import ConnectionInfos

exe = sys.executable.split(os.sep)[-1].split('.')[0]
IS_HOUDINI = exe in ["hindie", "houdinicore", "hescape", "houdinifx"]

class MetadataViewer(QtWidgets.QDialog):

    def __init__(self, object_path, parent=None):
        super(MetadataViewer, self).__init__(parent=parent)

        root, f = os.path.split(object_path)

        self.setWindowFlags(QtCore.Qt.Tool)
        self.setWindowTitle("Metadata viewer: " + f)

        metadata = cirrus_io.get_metadata(object_path)

        main_layout = QtWidgets.QVBoxLayout()

        data = []
        data.append(["Object path:", object_path])
        data.append(["Object Key:", cirrus_io.get_object_key(object_path)])

        if os.path.exists(object_path):
            size = os.path.getsize(object_path) * 0.000001
        else:
            size = 0.0
        s = '{0:.3f} Mb'.format(size)
        data.append(["Object local file size:", s])

        data.append(["Is on cloud:", str(cirrus_io.check_object(object_path) is not None)])
        data.append(["Is local:", str(os.path.exists(object_path))])

        if metadata:
            data.append(["Latest Upload User:", metadata.get("latest_upload_user", "-")])
            data.append(["Latest update:", metadata.get("latest_upload", "-")])
            data.append(["Upload message:", metadata.get("upload_message", "-")])
            data.append(["Extra Infos:", metadata.get("extra_infos", "-")])
            data.append(["Latest Upload User:", metadata.get("latest_upload_user", "-")])
            data.append(["User:", metadata.get("user", "-")])
            data.append(["Lock Message:", metadata.get("lock_message", "-")])
            data.append(["Lock Time:", metadata.get("lock_time", "-")])
            data.append(["Is Latest:", metadata.get("is_latest", "-")])

            refs = metadata.get("references")
            if refs:
                for i, ref in enumerate(refs):
                    data.append(["ref" + str(i) + ":", str(ref)])

            else:
                data.append(["References:", "None"])
        else:
            data.append(["No Metadata found locally", ""])

        for d, v in data:

            obj_lay = QtWidgets.QHBoxLayout()
            obj_lay.setAlignment(QtCore.Qt.AlignLeft)

            bold = QtGui.QFont()
            bold.setBold(True)
            ld = QtWidgets.QLabel(str(d))
            ld.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            ld.setStyleSheet("background-color: transparent;color: #436fdf")
            ld.setFont(bold)
            obj_lay.addWidget(ld)

            lv = QtWidgets.QLabel(str(v))
            lv.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            lv.setStyleSheet("background-color: transparent")
            obj_lay.addWidget(lv)

            main_layout.addLayout(obj_lay)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.close)
        main_layout.addWidget(close_btn)

        self.setLayout(main_layout)

class ActivityWidget(QtWidgets.QWidget):

    def __init__(self, *args):
        super(ActivityWidget, self).__init__(*args)
        
        self.main_layout = QtWidgets.QVBoxLayout()

        self.movie = QtGui.QMovie(ICONS + "loading.gif", parent=self)

        self.movie_screen = QtWidgets.QLabel()
        self.movie_screen.setSizePolicy(QtWidgets.QSizePolicy.Minimum, 
                                        QtWidgets.QSizePolicy.Minimum)        
        self.movie_screen.setAlignment(QtCore.Qt.AlignCenter)
        self.movie_screen.setMovie(self.movie)
        
        self.main_layout.addWidget(self.movie_screen)
        self.setLayout(self.main_layout)
        self.movie.start()

    def stop(self):
        self.movie.stop()

    def start(self):
        self.movie.start()

class GetFileFromCloudButton(QtWidgets.QPushButton):

    def __init__(self, panelfile, state, parent=None):
        super(GetFileFromCloudButton, self).__init__("")

        self.setObjectName("flatButton")
        self.panelfile = panelfile
        self.state = state
        self.parent_w = parent

        self.refresh_state(state)

    def mousePressEvent(self, event):

        if self.state == cirrus_objects.FileState.LOCAL_ONLY:
            return

        if event.button() == QtCore.Qt.RightButton:
            self.parent_w.open_versions()
        else:
            self.panelfile.get_from_cloud()

    def refresh_state(self, state):

        self.state = state

        if state == cirrus_objects.FileState.CLOUD_ONLY:
            self.setIcon(cirrus_io.get_icon("cloud_only.png"))
            self.setToolTip("File saved on cloud only\nClick to download the latest version.")

        elif state == cirrus_objects.FileState.METADATA_DESYNC:
            self.setIcon(cirrus_io.get_icon("cloud_meta_desync.png"))
            self.setToolTip("Warning: metadata desyncronized or missing\nDownload the latest version of the file to refresh the metadata.")

        elif state == cirrus_objects.FileState.LOCAL_ONLY:
            self.setIcon(cirrus_io.get_icon("cloud_close.png"))
            self.setToolTip("File saved only locally\nClick on save button to save it on the cloud.")

        elif state == cirrus_objects.FileState.CLOUD_AND_LOCAL_NOT_LATEST:
            self.setIcon(cirrus_io.get_icon("cloud_checkmark_not_latest.png"))
            self.setToolTip("Local version of the file is not the latest\nClick to download the latest version.\nRight-click to get older versions.")

        else:
            self.setIcon(cirrus_io.get_icon("cloud_checkmark.png"))
            self.setToolTip("File is up to date locally and on the cloud.\nRight-click to get older versions.")

class PanelFolder(QtWidgets.QFrame):

    def __init__(self, name="", path="", parent=None):
        super(PanelFolder, self).__init__(parent=parent)

        self.panel = parent

        self.path = path
        self.name = name

        self.setToolTip("Path: " + str(self.path))

        self.setAutoFillBackground(True)
        self.setObjectName("panelFolder")
        self.setFixedHeight(45)
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setSpacing(5)
        self.main_layout.setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignHCenter)
        self.ico = QtWidgets.QPushButton("")
        self.ico.setFlat(True)
        self.ico.setObjectName("folderIco")
        self.ico.setFixedHeight(28)
        self.ico.setIconSize(QtCore.QSize(26,26))
        self.ico.setStyleSheet("background-color: transparent;border: 0px")
        self.ico.setIcon(cirrus_io.get_icon("folder.svg"))
        self.main_layout.addWidget(self.ico)
        self.label = QtWidgets.QLabel(name)
        self.label.setObjectName("panelFolderLabel")
        self.main_layout.addWidget(self.label)
        self.setLayout(self.main_layout)
        self.setContentsMargins(15,0,0,0)
        self.init_buttons()

    def init_buttons(self):
        return

    def mouseDoubleClickEvent(self, event):

        main_ui = self.panel.main_ui
        bucket = ConnectionInfos.get("bucket")
        main_ui.show_panel(panel_name=self.name, panel_path=self.path)

class PanelFileButtons(QtWidgets.QWidget):

    def __init__(self, parent, state=cirrus_objects.FileState.NONE):
        super(PanelFileButtons, self).__init__(parent=parent)

        self.panelfile = parent
        self.metadata = None
        self.state_fetcher = None
        self.state = state
        self.local_file_path = self.panelfile.local_file_path
        self.is_locked = cirrus_objects.FileLockState.UNLOCKED

        self.buttons_layout = QtWidgets.QHBoxLayout()

        self.activity = ActivityWidget()
        self.activity.setFixedHeight(26)
        self.buttons_layout.addWidget(self.activity)
        self.activity.stop()
        self.activity.setVisible(False)

        self.save_to_cloud_button = QtWidgets.QPushButton("")
        self.save_to_cloud_button.setObjectName("flatButton")
        self.save_to_cloud_button.setIcon(cirrus_io.get_icon("cloud_save.png"))
        self.save_to_cloud_button.setIconSize(QtCore.QSize(26, 26))
        self.save_to_cloud_button.setFixedSize(QtCore.QSize(28, 28))
        self.save_to_cloud_button.setToolTip("Press this button to save the file to the cloud\n"
                                             "You must lock the file first")
        self.save_to_cloud_button.clicked.connect(self.panelfile.save_to_cloud)
        self.buttons_layout.addWidget(self.save_to_cloud_button)

        self.is_on_cloud_button = GetFileFromCloudButton(self.panelfile,
                                                         self.state,
                                                         parent=self)
        self.is_on_cloud_button.panelfile = self.panelfile
        self.is_on_cloud_button.setIconSize(QtCore.QSize(26, 26))
        self.is_on_cloud_button.setFixedSize(QtCore.QSize(28, 28))
        self.buttons_layout.addWidget(self.is_on_cloud_button)

        self.lock_button = QtWidgets.QPushButton("")
        self.lock_button.setObjectName("flatButton")
        self.lock_button.setIcon(cirrus_io.get_icon("notlocked.png"))
        self.lock_button.setIconSize(QtCore.QSize(26, 26))
        self.lock_button.setFixedSize(QtCore.QSize(28, 28))
        self.lock_button.clicked.connect(self.lock_file)
        self.buttons_layout.addWidget(self.lock_button)

        self.infos_button = QtWidgets.QPushButton("")
        self.infos_button.setObjectName("flatButton")
        self.infos_button.setIcon(cirrus_io.get_icon("info.svg"))
        self.infos_button.setIconSize(QtCore.QSize(26, 26))
        self.infos_button.setFixedSize(QtCore.QSize(28, 28))
        self.infos_button.clicked.connect(self.open_infos)
        self.buttons_layout.addWidget(self.infos_button)

        self.refresh_button = QtWidgets.QPushButton("")
        self.refresh_button.setIconSize(QtCore.QSize(26, 26))
        self.refresh_button.setFixedSize(QtCore.QSize(28, 28))
        self.refresh_button.setObjectName("flatButton")
        self.refresh_button.setToolTip("Refresh current file metadata")
        self.refresh_button.setIcon(cirrus_io.get_icon("reload.svg"))
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

    def start_state_refreshing(self):

        self.activity.start()
        self.activity.setVisible(True)

        self.save_to_cloud_button.setVisible(False)
        self.is_on_cloud_button.setVisible(False)
        self.lock_button.setVisible(False)
        self.infos_button.setVisible(False)
        self.refresh_button.setVisible(False)

    def end_state_refreshing(self, state, metadata):

        self.activity.stop()
        self.activity.setVisible(False)

        self.is_on_cloud_button.refresh_state(state)

        self.metadata = metadata
        self.state = state
        
        self.save_to_cloud_button.setVisible(True)
        self.is_on_cloud_button.setVisible(True)
        self.lock_button.setVisible(True)
        self.infos_button.setVisible(True)
        self.refresh_button.setVisible(True)

        lock_user = metadata.get("user", "")
        lock_message = metadata.get("lock_message", "No message")
        lock_time = metadata.get("lock_time", "No Timestamp")

        if lock_user == "":
            self.is_locked = cirrus_objects.FileLockState.UNLOCKED
            self.lock_button.setIcon(cirrus_io.get_icon("notlocked.png"))
            self.lock_button.setToolTip("File not locked")

        elif lock_user == cirrus_objects.ObjectMetadata.get_user_uid():
            self.is_locked = cirrus_objects.FileLockState.SELF_LOCKED
            self.lock_button.setIcon(cirrus_io.get_icon("lock_self.png"))
            tooltip = ("File locked by: " + lock_user + '\n'
                       "Message: " + lock_message + '\n'
                       "Locked since: " + lock_time + "")
            self.lock_button.setToolTip(tooltip)
        else:
            self.is_locked = cirrus_objects.FileLockState.LOCKED
            self.lock_button.setIcon(cirrus_io.get_icon("locked.png"))
            tooltip = ("File locked by: " + lock_user + '\n'
                       "Message: " + lock_message + '\n'
                       "Locked since: " + lock_time + "")
            self.lock_button.setToolTip(tooltip)

        self.state_fetcher = None

    def refresh_state(self):
        
        state_fetcher = cirrus_threading.FetchStateThread(self.local_file_path)
        state_fetcher.signals.end_sgn.connect(self.end_state_refreshing)
        state_fetcher.signals.start_sgn.connect(self.start_state_refreshing)
        QtCore.QThreadPool.globalInstance().start(state_fetcher)

    def lock_file(self):

        Logger.Log.debug("Refresh state before locking file")
        state, metadata = cirrus_io.refresh_state(self.local_file_path)
        self.end_state_refreshing(state, metadata)

        # if not on cloud, you can't lock the file
        if self.state == cirrus_objects.FileState.LOCAL_ONLY:
            Logger.Log.debug("Trying to lock a local-only file: " + self.local_file_path)
            QtWidgets.QMessageBox.warning(self, "Error",
                                          ("Trying to lock a local-only file,\n"
                                           "Send the object on the cloud first."))
            return

        if self.state == cirrus_objects.FileState.CLOUD_ONLY:
            Logger.Log.debug("Trying to lock a cloud-only file: " + self.local_file_path)
            QtWidgets.QMessageBox.warning(self, "Error",
                                          ("Trying to lock a cloud-only file,\n"
                                           "Get the latest version from the cloud first."))
            return

        if self.is_locked == cirrus_objects.FileLockState.LOCKED:
            QtWidgets.QMessageBox.warning(self, "Error", "File already locked")
            return

        if self.is_locked == cirrus_objects.FileLockState.SELF_LOCKED:

            ico = QtWidgets.QMessageBox.Warning
            confirm_msg = "Do you want to unlock the file ?"
            ask = QtWidgets.QMessageBox(ico, "Confirm", confirm_msg,
                                        buttons = QtWidgets.QMessageBox.StandardButton.Yes|\
                                                  QtWidgets.QMessageBox.StandardButton.No,
                                        parent=self)
            geo = ask.frameGeometry()
        
            ask.move(QtGui.QCursor.pos() - ( geo.topRight() * 3 ))
            ask.setStyleSheet("""QMessageBox{background-color: #3e5975}
                                 QFrame{background-color: #3e5975}
                                 QLabel{background-color: #3e5975}""")
            if ask.exec_() == QtWidgets.QMessageBox.StandardButton.No:
                return
            
            toggle = False
        else:
            toggle = True

        lock_message = ""

        if toggle:
            ask_lock_message = cirrus_widgets_inputs.MessageInput(False, True, self)
            ask_lock_message.exec_()
            lock_message = ask_lock_message.message
            if ask_lock_message.cancel:
                return
        
        m = cirrus_io.lock_object(object_path=self.local_file_path,
                                toggle=toggle,
                                lock_message=lock_message)

        if toggle:
            self.is_locked = cirrus_objects.FileLockState.SELF_LOCKED
            tooltip = ("File locked by: " + m.get("user", "") + '\n'
                       "Message: " + m.get("lock_message", "No Message") + '\n'
                       "Locked since: " + m.get("lock_time", "No timestamp") + "")
            self.lock_button.setIcon(cirrus_io.get_icon("lock_self.png"))
            self.lock_button.setToolTip(tooltip)
        else:
            self.is_locked = cirrus_objects.FileLockState.UNLOCKED
            self.lock_button.setIcon(cirrus_io.get_icon("notlocked.png"))
            self.lock_button.setToolTip("File not locked")

        if self.panelfile.plugin:
            self.panelfile.plugin.exec_on_lock(path=self.local_file_path)

    def open_versions(self):

        version_picker = cirrus_versions_getter.VersionPicker(self.local_file_path,
                                                            parent=self)
        version_picker.exec_()

        ver = version_picker.version_selected
        if not ver: return

        self.panelfile.get_from_cloud(version_id=ver)

    def open_infos(self):

        MetadataViewer(self.local_file_path, self).exec_()

class PanelFile(PanelFolder):

    def __init__(self, name="", path="", state=cirrus_objects.FileState.NONE, parent=None):

        self.state = state
        self.icon_menu = None
        self.worker = None
        self.plugin = None
        root = ConnectionInfos.get("local_root")
        
        self.local_file_path = root + path
        if os.path.exists(self.local_file_path):
            self.local_file_size = os.path.getsize(self.local_file_path) * 0.000001
        else:
            self.local_file_size = 0.0

        super(PanelFile, self).__init__(name=name, path=path, parent=parent)
        self.setObjectName("panelFile")
        self.label.setObjectName("panelFileLabel")
        self.setToolTip("Local path: " + self.local_file_path + '\n' + \
                        "Cloud path: " + path + '\n' + \
                        "File Size: " + '{0:.3f}'.format(self.local_file_size) + " mb")

    def init_buttons(self):

        file_extension = self.path.split('.')[-1]
        icon = ICONS + "file_types/" + file_extension + ".svg"
        if not os.path.exists(icon):
            self.ico.setIcon(cirrus_io.get_icon("document.svg"))
        else:
            self.ico.setIcon(QtGui.QIcon(icon))
        self.ico.setObjectName("fileIco")
        
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
        self.activity_upload_ico.setObjectName("activityWidget")
        self.activity_upload_ico.setFixedHeight(29)
        self.activity_upload_ico.setFixedWidth(29)
        self.upload_movie = QtGui.QMovie(ICONS + "upload.gif", parent=self)
        self.activity_upload_ico.setMovie(self.upload_movie)
        self.activity_upload_ico.setVisible(False)
        self.main_layout.addWidget(self.activity_upload_ico)

        self.activity_download_ico = QtWidgets.QLabel()
        self.activity_download_ico.setObjectName("activityWidget")
        self.activity_download_ico.setFixedHeight(29)
        self.activity_download_ico.setFixedWidth(29)
        self.download_movie = QtGui.QMovie(ICONS + "download.gif", parent=self)
        self.activity_download_ico.setMovie(self.download_movie)
        self.activity_download_ico.setVisible(False)
        self.main_layout.addWidget(self.activity_download_ico)

        self.buttons_layout = QtWidgets.QHBoxLayout()
        self.buttons_layout.addStretch(1)
        self.buttons_layout.setAlignment(QtCore.Qt.AlignRight)

        self.file_buttons = PanelFileButtons(self, state=self.state)
        self.buttons_layout.addWidget(self.file_buttons)

        self.main_layout.addLayout(self.buttons_layout)
        
        self.plugin = None
        self.init_plugin()
        
    def init_plugin(self):
        """ Init plugin if file extension matches any loaded plugins
        """
        root, f = os.path.split(self.local_file_path)
        ex = f.split('.', 1)[-1]

        if not ex in cirrus_plugin_parser.PluginRepository.VALID_FILES:
            return

        for plugin in cirrus_plugin_parser.PluginRepository.PLUGINS:
            if ex in plugin.files:
                self.plugin = plugin
                break
        self.plugin = plugin
        self.icon_menu = plugin.on_icon_clicked_menu(parent=self,
                                                     path=self.local_file_path,
                                                     local_root=ConnectionInfos.get("local_root"),
                                                     cloud_path=self.path)
        
        if self.icon_menu:
            self.ico.clicked.connect(lambda: self.icon_menu.popup(QtGui.QCursor.pos()))

    def mouseDoubleClickEvent(self, event):

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
            s = cirrus_io.get_object_size(self.local_file_path)
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

        ico = cirrus_io.get_icon("cloud_checkmark.png")
        self.file_buttons.is_on_cloud_button.setIcon(ico)

        self.file_buttons.refresh_state()

        # check if a plugin is loaded, if yes, execute the "on_get" method of the plugin
        if self.plugin:
            if mode == 0:
                self.plugin.exec_on_save(path=self.local_file_path)
            else:
                self.plugin.exec_on_get(path=self.local_file_path)

    def get_from_cloud(self, version_id=""):

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
        
        if ask.exec_() == QtWidgets.QMessageBox.StandardButton.No: return

        self.activity_progress.setVisible(True)

        worker = cirrus_threading.FileIOThread(self.local_file_path, mode=1,
                                             version_id=version_id)
       
        worker.signals.start_sgn.connect(self.start_progress)
        worker.signals.end_sgn.connect(self.end_progress)
        worker.signals.update_progress_sgn.connect(self.update_progress)

        QtCore.QThreadPool.globalInstance().start(worker)

    def save_to_cloud(self):

        if not self.file_buttons.state == cirrus_objects.FileState.LOCAL_ONLY:
            if not self.file_buttons.is_locked == cirrus_objects.FileLockState.SELF_LOCKED:
                QtWidgets.QMessageBox.warning(self, "Error", "Can't save object to cloud, you have to lock the file first")
                return

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
        
        if ask.exec_() == QtWidgets.QMessageBox.StandardButton.No: return
        
        ask_msg = cirrus_widgets_inputs.MessageInput(parent=self)
        ask_msg.move(QtGui.QCursor.pos() - ( geo.topRight() * 3 ))
        ask_msg.exec_()

        if ask_msg.cancel:
            return

        msg = ask_msg.message
        if msg.strip() == "":
            return
        keep_locked = ask_msg.keep_locked

        self.activity_progress.setVisible(True)

        s = os.path.getsize(self.local_file_path)
        self.activity_progress.setMaximum(s)

        self.worker = cirrus_threading.FileIOThread(self.local_file_path, message=msg,
                                                  keep_locked=keep_locked)
       
        self.worker.signals.start_sgn.connect(self.start_progress)
        self.worker.signals.end_sgn.connect(self.end_progress)
        self.worker.signals.update_progress_sgn.connect(self.update_progress)
        
        QtCore.QThreadPool.globalInstance().start(self.worker)

class Panel(QtWidgets.QFrame):

    def __init__(self, panel_name="", panel_folder_path="", subfolder="", parent=None):
        super(Panel, self).__init__(parent=parent)

        self.main_ui = parent

        self.subfolder = subfolder
        self.fetcher = None
        self.cur_folder_id = 0
        self.panel_name = panel_name
        
        self.setProperty("houdiniStyle", IS_HOUDINI)
        self.setObjectName("panelBase")
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
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
        self.ico.setPixmap(cirrus_io.get_icon("folder_open.svg").pixmap(28, 28))

        self.header_layout.addWidget(self.ico)
        lbl = QtWidgets.QLabel(panel_name.split('/')[-1])
        lbl.setObjectName("headerLabel")
        self.header_layout.addWidget(lbl)
        self.header_layout.addStretch(1)

        self.activity_w = ActivityWidget()
        self.activity_w.setVisible(False)
        self.header_layout.addWidget(self.activity_w)

        self.refresh_button = QtWidgets.QPushButton("")
        self.refresh_button.setFixedHeight(28)
        self.refresh_button.setFixedWidth(28)
        self.refresh_button.setIconSize(QtCore.QSize(26, 26))
        self.refresh_button.setObjectName("headerButton")
        self.refresh_button.clicked.connect(lambda: self.init_fetching(reset=True))
        self.refresh_button.setToolTip("Refresh current folder state")
        self.refresh_button.setIcon(cirrus_io.get_icon("reload.svg"))
        self.header_layout.addWidget(self.refresh_button)
        self.header.setLayout(self.header_layout)
        self.main_layout.addWidget(self.header)

        # elements
        self.elements = []
        self.element_scroll = QtWidgets.QScrollArea()
        self.element_scroll.setObjectName("elementScroll")
        self.element_scroll.setWidgetResizable(True)
        self.elements_layout = QtWidgets.QVBoxLayout()
        self.elements_layout.setAlignment(QtCore.Qt.AlignTop)
        self.elements_layout.setSpacing(0)
        self.elements_layout.setContentsMargins(0, 0, 0, 0)
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
            #self.fetcher.wait(2)
            self.fetcher = None
            time.sleep(1)

        self.fetcher = cirrus_threading.ElementFetcherThread()
        self.fetcher.bucket = ConnectionInfos.get("bucket")
        self.fetcher.folder_name = self.subfolder
        self.fetcher.signals.add_folder.connect(self.add_folder)
        self.fetcher.signals.add_element.connect(self.add_element)
        self.fetcher.signals.start_sgn.connect(self.element_fetching_start)
        self.fetcher.signals.end.connect(self.element_fetching_end)
        QtCore.QThreadPool.globalInstance().start(self.fetcher)
        
    def refresh_plugin(self):
        
        Logger.Log.debug("Refreshing plugins for folder id: " + str(self.cur_folder_id))
        for n in [w for w in self.elements if isinstance(w, PanelFile)]:
            n.init_plugin()

    def add_element(self, f):

        file_name = f.split('/')[-1]
        w = PanelFile(name=file_name, path=f, parent=self)
        self.elements.append(w)
        self.elements_layout.addWidget(w)

    def add_folder(self, f):
        
        folder_name = f.split('/')[-1]
        w = PanelFolder(name=folder_name, path=f+'/', parent=self)
        self.elements.append(w)
        self.elements_layout.insertWidget(self.cur_folder_id, w)
        self.cur_folder_id += 1

    def element_fetching_start(self):

        self.cur_folder_id = 0
        self.refresh_button.setVisible(False)
        self.activity_w.setVisible(True)

    def element_fetching_end(self):

        self.refresh_button.setVisible(True)
        self.activity_w.setVisible(False)

    def element_fetched(self, data):

        if data is None: return
        
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
            w = PanelFile(name=file_name, path=f, state=cirrus_objects.FileState.LOCAL_ONLY,
                          parent=self)
            self.elements.append(w)
            self.elements_layout.addWidget(w)
        
        self.activity_w.setVisible(False)