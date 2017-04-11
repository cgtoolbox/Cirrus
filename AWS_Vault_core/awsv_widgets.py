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
from AWS_Vault_core import awsv_widgets_panels as panels
reload(panels)

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

class MainWidget(QtWidgets.QFrame):

    config = awsv_config.Config()

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
        self.open_root_act = QtWidgets.QAction("Create new project", self)
        self.close_root_act = QtWidgets.QAction("Download a project", self)
        self.file_menu.addAction(self.open_root_act)
        self.file_menu.addAction(self.close_root_act)
        self.options_menu = self.main_menu.addMenu("Options")
        self.auto_check_state_act = QtWidgets.QAction("Auto Check Files State", self)
        self.auto_check_state_act.setCheckable(True)
        self.options_menu.addAction(self.auto_check_state_act)
        
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
            
            panel = panels.Panel(panel_name, panel_path, subfolder=panel_path, parent=self)
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

        self.pathbar = pathbar.PathBar(root = bucket_name, parent=self)
        self.main_layout.addWidget(self.pathbar)
        
        p = panels.Panel(bucket_name, root, subfolder="", parent=self)
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