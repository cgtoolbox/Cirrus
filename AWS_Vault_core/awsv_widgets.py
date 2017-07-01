import os
import sys
import tempfile
from AWS_Vault_core.awsv_logger import Logger
from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtCore
import botocore
from AWS_Vault_core import awsv_io
reload(awsv_io)
from AWS_Vault_core import awsv_threading
reload(awsv_threading)
from AWS_Vault_core import awsv_objects
reload(awsv_objects)
from AWS_Vault_core import awsv_config
reload(awsv_config)
from AWS_Vault_core import awsv_widgets_pathbar as pathbar
reload(pathbar)
from AWS_Vault_core import awsv_widgets_panels as panels
reload(panels)
from AWS_Vault_core import awsv_plugin_parser
reload(awsv_plugin_parser)
from AWS_Vault_core import awsv_plugin_manager
reload(awsv_plugin_manager)
from AWS_Vault_core.awsv_connection import ConnectionInfos
from AWS_Vault_core.awsv_connection import init_connection
from AWS_Vault_core import awsv_io
reload(awsv_io)

ICONS = os.path.dirname(__file__) + "\\icons\\"

exe = sys.executable.split(os.sep)[-1].split('.')[0]
IS_HOUDINI = exe in ["hindie", "houdinicore", "hescape", "houdinifx"]

class ProjectSelector(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(ProjectSelector, self).__init__(parent=parent)
        
        self.main_ui = parent
        
        main_layout = QtWidgets.QVBoxLayout()
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        main_layout.setAlignment(QtCore.Qt.AlignCenter)
        
        self.open_project_button = QtWidgets.QPushButton(" Open a project")
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

class ProjectGetter(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(ProjectGetter, self).__init__(parent=parent)

        self.setProperty("houdiniStyle", IS_HOUDINI)

        self.mainui = parent

        self.setWindowTitle("Get Project From Cloud")
        self.setWindowIcon(QtGui.QIcon(ICONS + "inbox.svg"))
        self.setFixedHeight(170)
        
        init_connection()
        self.client = ConnectionInfos.get("s3_client")
        self.resource = ConnectionInfos.get("s3_resource")

        self.worker = None
        self.prj_path = ""

        cw = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)

        # project to load
        prj_list_layout = QtWidgets.QHBoxLayout()
        prj_list_layout.setSpacing(31)
        prj_list_layout.setAlignment(QtCore.Qt.AlignLeft)
        prj_list_layout.addWidget(QtWidgets.QLabel("Project:"))
        self.project_list = QtWidgets.QComboBox()
        self.project_list.addItems(self.list_bucket())
        prj_list_layout.addWidget(self.project_list)
        main_layout.addLayout(prj_list_layout)

        # local path
        self.local_path = ""
        tgt_folder_layout = QtWidgets.QHBoxLayout()
        tgt_folder_layout.addWidget(QtWidgets.QLabel("Local Folder:"))
        self.local_folder_input = QtWidgets.QLineEdit()
        self.local_folder_input.setMinimumWidth(350)
        self.local_folder_input.textChanged.connect(self.update_local_folder_input)
        tgt_folder_layout.addWidget(self.local_folder_input)
        self.pick_folder_btn = QtWidgets.QPushButton("...")
        self.pick_folder_btn.clicked.connect(self.get_local_dir)
        tgt_folder_layout.addWidget(self.pick_folder_btn)
        main_layout.addLayout(tgt_folder_layout)

        # progress bars
        self.nelements_lbl = QtWidgets.QLabel("-")
        main_layout.addWidget(self.nelements_lbl)
        self.elements_progress = QtWidgets.QProgressBar()
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

        self.start_btn = QtWidgets.QPushButton("Start")
        self.start_btn.setIconSize(QtCore.QSize(32, 32))
        self.start_btn.setIcon(QtGui.QIcon(ICONS + "checkmark.svg"))
        self.start_btn.clicked.connect(self.start_download)

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setIconSize(QtCore.QSize(32, 32))
        self.cancel_btn.setIcon(QtGui.QIcon(ICONS + "close.svg"))
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_download)

        main_layout.addWidget(self.start_btn)
        main_layout.addWidget(self.cancel_btn)

        cw.setLayout(main_layout)
        self.setCentralWidget(cw)

    def update_local_folder_input(self):

        self.local_path = self.local_folder_input.text()

    def get_local_dir(self):

        r = QtWidgets.QFileDialog.getExistingDirectory(self, "Pick Local Folder")
        if not r:
            return None

        self.local_path = r
        self.local_folder_input.setText(r)

    def list_bucket(self):

        raw = self.client.list_buckets()
        buckets = [ b["Name"] for b in raw["Buckets"] if \
                    b["Name"].startswith("prj-")]
        return buckets

    def check_bucket(self, bucket_name):

        try:
            self.client.head_bucket(Bucket=bucket_name)
            return True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] in ["404", "403"]:
                print "check_bucket error: " + e.response['Error']['Code']
                return False
            raise e

    def start_process(self):

        self.start_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.elements_progress.setMinimum(0)
        self.elements_progress.setMaximum(0)
        self.nelements_lbl.setText("Fetching files...")

    def start_download_item(self, item_name, item_size):

        self.elements_progress.setMinimum(0)
        self.elements_progress.setMaximum(item_size)
        self.elements_progress.setValue(0)
        self.nelements_lbl.setText(item_name)

    def update_element_progress(self, b):

        n = self.elements_progress.value() + b
        self.elements_progress.setValue(n)

    def download_done(self, statue, n_items, msg, global_size):

        if statue > 0:
            global_size = '{0:.3f} Mb'.format(global_size * 0.000001)
            txt = str(n_items) + " elements downloaded in " + msg + ", Total size: " + global_size
        elif statue == 0:
            txt = "Download cancelled, {} elements downloaded.".format(n_items)
        else:
            txt = "ERROR: elements downloaded in " + msg

        self.nelements_lbl.setText(txt)
        self.start_btn.setVisible(True)
        self.cancel_btn.setVisible(False)

        if os.path.exists(self.prj_path) and self.mainui:
            r = QtWidgets.QMessageBox.question(self, "Open project",
                                               "Open the project: {} ?".format(self.prj_path))
            if r == QtWidgets.QMessageBox.Yes:
                self.mainui.init_root(self.prj_path)

        self.close()

    def cancel_download(self):

        if self.worker is not None:
            self.worker.cancel = True
            self.worker.wait()

    def start_download(self):

        if not os.path.exists(self.local_path):
            QtWidgets.QMessageBox.critical(self, "Error", "Local folder doesn't exist")
            return

        bucket_name = self.project_list.currentText()
        if not self.check_bucket(bucket_name):
            QtWidgets.QMessageBox.critical(self, "Error", "Can't access project: " + bucket_name)
            return

        ico = QtWidgets.QMessageBox.Question
        ask = QtWidgets.QMessageBox(ico, "Confirm", "Download project: " + bucket_name + " ?",
                                    buttons = QtWidgets.QMessageBox.StandardButton.Yes|\
                                              QtWidgets.QMessageBox.StandardButton.No,
                                    parent=self)
        if ask.exec_() == QtWidgets.QMessageBox.StandardButton.No: return

        bucket = awsv_io.get_bucket(bucket_name)

        if self.worker is not None:
            self.worker.wait(1)
            self.worker = None

        prj_path = self.local_path + '/' + bucket_name
        if not os.path.exists(prj_path):
            os.makedirs(prj_path)

        Logger.Log.info("Downloading project: " + bucket_name)
        Logger.Log.info("Local path: " + prj_path)

        self.prj_path = prj_path
        self.worker = awsv_threading.DownloadProjectThread(bucket, prj_path)
        self.worker.start_sgn.connect(self.start_process)
        self.worker.start_element_download_sgn.connect(self.start_download_item)
        self.worker.update_download_progress_sgn.connect(self.update_element_progress)
        self.worker.end_sgn.connect(self.download_done)
        self.worker.start()

class MainWidget(QtWidgets.QFrame):

    def __init__(self, parent=None):
        super(MainWidget, self).__init__(parent=parent)

        awsv_plugin_parser.get_plugin()

        self.setProperty("houdiniStyle", IS_HOUDINI)
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setObjectName("Vault")
        self.setWindowTitle("Vault")

        self.pathbar = None
        self.panels = {}
        self.cur_panel = None
        self.root_panel = None
        self.plug_manager_w  = None
        self.project_getter = None

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(1,1,1,1)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.main_menu = QtWidgets.QMenuBar(self)
        self.main_menu.setFixedHeight(25)
        self.file_menu = self.main_menu.addMenu("File")

        self.open_proj_act = QtWidgets.QAction("Open a project", self)
        self.open_proj_act.setIcon(QtGui.QIcon(ICONS + "folder_open.svg"))
        self.open_proj_act.triggered.connect(self.init_root)
        self.close_proj_act = QtWidgets.QAction("Close Project", self)
        self.close_proj_act.setIcon(QtGui.QIcon(ICONS + "close.svg"))
        self.close_proj_act.triggered.connect(self.close_project)
        self.download_proj_act = QtWidgets.QAction("Download a project", self)
        self.download_proj_act.triggered.connect(self.get_project)
        self.download_proj_act.setIcon(QtGui.QIcon(ICONS + "inbox.svg"))
        self.file_menu.addAction(self.open_proj_act)
        self.file_menu.addAction(self.close_proj_act)
        self.file_menu.addAction(self.download_proj_act)
        self.options_menu = self.main_menu.addMenu("Options")
        self.auto_check_state_act = QtWidgets.QAction("Auto Check Files State", self)
        self.auto_check_state_act.setCheckable(True)
        self.options_menu.addAction(self.auto_check_state_act)
        self.options_menu.addSeparator()
        self.open_plug_manager_act = QtWidgets.QAction("Plugin Manager", self)
        self.open_plug_manager_act.setIcon(QtGui.QIcon(ICONS + "plugin.svg"))
        self.open_plug_manager_act.triggered.connect(self.open_plugin_manager)
        self.options_menu.addAction(self.open_plug_manager_act)
        self.refresh_plugins_act = QtWidgets.QAction("Refresh Plugins", self)
        self.refresh_plugins_act.setIcon(QtGui.QIcon(ICONS + "reload.svg"))
        self.refresh_plugins_act.triggered.connect(self.refresh_plugins)
        self.options_menu.addAction(self.refresh_plugins_act)
        
        self.main_layout.addWidget(self.main_menu)

        self.init_button = ProjectSelector(self)
        self.main_layout.addWidget(self.init_button)

        self.setLayout(self.main_layout)

    def open_plugin_manager(self):

        self.plug_manager_w = awsv_plugin_manager.PluginManager(self)
        self.plug_manager_w.show()

    def refresh_plugins(self):

        for p in self.panels.itervalues():
            p.refresh_plugin()

    def close_project(self):

        if not self.cur_panel: return

        QtCore.QThreadPool.globalInstance().waitForDone(1)

        for panel in self.panels.itervalues():

            panel.bucket = None
            panel.setParent(None)
            panel.deleteLater()

        self.pathbar.setParent(None)
        self.pathbar.deleteLater()

        self.cur_panel = None
        self.panels = {}

        self.init_button.setVisible(True)

    def get_project(self):

        self.project_getter = ProjectGetter(self)
        self.project_getter.show()

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

        bucket_name = ConnectionInfos.get("bucket_name")
        panel_id = bucket_name + '/' + panel_path

        panel = self.panels.get(panel_id)
        if panel:
            panel.setVisible(True)
        
        else:
            
            panel = panels.Panel(panel_name, panel_path, subfolder=panel_path, parent=self)
            self.main_layout.addWidget(panel)
            self.panels[panel_id] = panel

        self.cur_panel = panel
        self.pathbar.set_current_level(panel_path)

    def init_root(self, root=""):

        if self.cur_panel is not None:
            self.close_project()
        
        if not root:
            root = QtWidgets.QFileDialog.getExistingDirectory(self, "Pick a root folder")
            if not root: return

        root = root.replace('\\', '/')
        bucket_name = root.split('/')[-1]
        Logger.Log.info("Init root: " + root)

        # init the connection informations singleton
        init_connection(bucket_name=bucket_name, local_root=root, reset=True)

        bucket = ConnectionInfos.get("bucket")
        if not bucket:
            QtWidgets.QMessageBox.critical(self, "Error", "Can't open root: {}.\nDoes the folder exist on the cloud ?".format(root))
            return False

        self.init_button.setVisible(False)

        self.pathbar = pathbar.PathBar(root = bucket_name, parent=self)
        self.main_layout.addWidget(self.pathbar)
        
        p = panels.Panel(bucket_name, root, subfolder="", parent=self)
        self.panels[bucket_name + '/'] = p
        self.main_layout.addWidget(p)
        self.cur_panel = p
        self.root_panel = p

        # add to history
        history_file = tempfile.gettempdir() + os.sep + "aws_vault_projects"
        if not os.path.exists(history_file):
            with open(history_file, 'w') as f:
                f.write(root + '\n')
        else:
            with open(history_file, 'r') as f:
                history = f.readlines()

            if root + '\n' in history:
                return

            if len(history) > 10:
                history.pop(0)
                history.append(root + '\n')
                with open(history_file, 'w') as f:
                    f.writelines(history)
            else:
                with open(history_file, 'a') as f:
                    f.write(root + '\n')

    def closeEvent(self, event):
        
        QtCore.QThreadPool.globalInstance().waitForDone(1)

        for panel in self.panels.itervalues():            
            panel.bucket = None

        super(MainWidget, self).closeEvent(event)
        
        
