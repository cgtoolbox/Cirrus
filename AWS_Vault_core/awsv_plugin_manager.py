import os
import sys

from PySide2 import QtGui
from PySide2 import QtCore
from PySide2 import QtWidgets

from AWS_Vault_core import awsv_plugin_parser
reload(awsv_plugin_parser)

from AWS_Vault_core import py_highlighter
reload(py_highlighter)

ICONS = os.path.dirname(__file__) + "\\icons\\"

class PluginEntries(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(PluginEntries, self).__init__(parent=parent)

        self.plugin_manager = parent

        self.plugin_settings = awsv_plugin_parser.PluginSettings()
        self.plugins = self.plugin_settings.plugins

        self.setProperty("houdiniStyle", True)
        self.plugin_names = [n.get_plugin_name() for n in self.plugins]

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignLeft)

        main_layout.addWidget(QtWidgets.QLabel("Plugin: "))

        self._adding_item = False
        self.plugins_combo = QtWidgets.QComboBox()
        self.plugins_combo.addItems(self.plugin_names)
        self.plugins_combo.addItem(QtGui.QIcon(ICONS + "add.svg"), "Create")

        main_layout.addWidget(self.plugins_combo)

        main_layout.addWidget(QtWidgets.QLabel("Executable(s):"))
        self.p_fam_executables = QtWidgets.QLineEdit()
        main_layout.addWidget(self.p_fam_executables)

        add_cur_exe_btn = QtWidgets.QPushButton("")
        add_cur_exe_btn.setFixedHeight(32)
        add_cur_exe_btn.setFixedWidth(32)
        add_cur_exe_btn.setIcon(QtGui.QIcon(ICONS + "down.svg"))
        add_cur_exe_btn.setIconSize(QtCore.QSize(25, 25))
        add_cur_exe_btn.setToolTip("Add current running executable to the list")
        add_cur_exe_btn.clicked.connect(self.add_cur_exec)
        main_layout.addWidget(add_cur_exe_btn)

        rename_fam_btn = QtWidgets.QPushButton("")
        rename_fam_btn.setFixedHeight(32)
        rename_fam_btn.setFixedWidth(32)
        rename_fam_btn.setIcon(QtGui.QIcon(ICONS + "edit.svg"))
        rename_fam_btn.setIconSize(QtCore.QSize(25, 25))
        rename_fam_btn.setToolTip("Rename selected familly")
        main_layout.addWidget(rename_fam_btn)

        main_layout.setContentsMargins(0,0,0,0)
        self.setLayout(main_layout)

        self.plugins_combo.currentIndexChanged.connect(self.update_selected_familly)
        self.update_selected_familly()

        self.selected_familly = self.plugins_combo.currentText()

    def update_selected_familly(self):

        if self.plugins_combo.currentText() == "Create":
            
            if self._adding_item: return

            fam_name, ok = QtWidgets.QInputDialog.getText(self, 'Enter Name', 'Enter plugin name')
            if ok:
                self._adding_item = True
                c = self.plugins_combo.count()
                self.plugins_combo.insertItem(c-1, fam_name)
                self.plugins_combo.setCurrentText(fam_name)
                self.p_fam_executables.setText("")
            else:
                self.plugins_combo.setCurrentText(self.selected_familly)

            self._adding_item = False
            return

        selected_plugin = [n for n in self.plugins \
            if n.get_plugin_name() == self.plugins_combo.currentText()][0]

        selected_fam_exec = selected_plugin.get_plugin_exe()

        self.p_fam_executables.setText(', '.join(selected_fam_exec))
        self.selected_familly = self.plugins_combo.currentText()
        
        # display selected plugin in plugin manager
        self.plugin_manager.display_file_infos(self.plugins_combo.currentText(),
                                               selected_plugin)

    def add_cur_exec(self):

        r, cur_exe = os.path.split(sys.executable)
        if cur_exe.endswith(".exe"): cur_exe = cur_exe[0:-4]
        cur_list = self.p_fam_executables.text().replace(' ', '').split(',')
        cur_list = [c for c in cur_list if c != ""]
        if cur_exe in cur_list:
            QtWidgets.QMessageBox.warning(self, "Warning",
                                          "Current executable '{}' already in the list".format(cur_exe))
            return

        cur_list.append(cur_exe)
        self.p_fam_executables.setText(', '.join(cur_list))

class CodeEditor(QtWidgets.QPlainTextEdit):

    def __init__(self, parent=None):
        super(CodeEditor, self).__init__(parent=parent)
        
        self.setStyleSheet("background-color: #161616")
        py_highlighter.PythonHighlighter(self.document())

    def keyPressEvent(self, e):
        
        # change tab to 4 spaces
        if e.key() == QtCore.Qt.Key_Tab:
            e = QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                QtCore.Qt.Key_Tab,
                                QtCore.Qt.KeyboardModifier.NoModifier,
                                text="    ")
            e.accept()
        super(CodeEditor, self).keyPressEvent(e)

class PluginInfos(QtWidgets.QWidget):

    def __init__(self, plugin_infos, parent=None):
        super(PluginInfos, self).__init__(parent=parent)

        self.plugin_infos = plugin_infos
        self.bindings = {}
        self.methods = {}
        self.script_code = self.plugin_infos.script_code

        r = self.plugin_infos.get("files,uid", level="bindings")
        if r:
            for files, uid in r:
                self.bindings[', '.join(files)] = uid
                self.methods[', '.join(files)] = self.plugin_infos.get("methods", level="bindings", uid=uid)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.file_bindings_lay = QtWidgets.QHBoxLayout()
        self.file_bindings_lay.setAlignment(QtCore.Qt.AlignLeft)
        self.file_bindings_lay.addWidget(QtWidgets.QLabel("File Bindings:"))

        self.file_bindins_combo = QtWidgets.QComboBox()
        self.file_bindins_combo.addItems([v for v in self.bindings.iterkeys()])
        self.file_bindins_combo.addItem(QtGui.QIcon(ICONS + "add.svg"), "Create")
        self.file_bindings_lay.addWidget(self.file_bindins_combo)
        
        edit_files_btn = QtWidgets.QPushButton("")
        edit_files_btn.setFixedHeight(32)
        edit_files_btn.setFixedWidth(32)
        edit_files_btn.setIcon(QtGui.QIcon(ICONS + "edit.svg"))
        edit_files_btn.setIconSize(QtCore.QSize(25, 25))
        edit_files_btn.setToolTip("Edit files list")
        self.file_bindings_lay.addWidget(edit_files_btn)

        self.main_layout.addLayout(self.file_bindings_lay)

        actions_lay = QtWidgets.QHBoxLayout()
        actions_lay.setAlignment(QtCore.Qt.AlignLeft)
        actions_lay.addWidget(QtWidgets.QLabel("Action:"))

        self.actions_combo = QtWidgets.QComboBox()
        self.actions_combo.addItem(QtGui.QIcon(ICONS + "cloud_checkmark.png"),"On Get")
        self.actions_combo.addItem(QtGui.QIcon(ICONS + "cloud_save.png"),"On Save")
        self.actions_combo.addItem(QtGui.QIcon(ICONS + "lock_self.png"),"On Lock")
        self.actions_combo.addItem(QtGui.QIcon(ICONS + "txt.svg"),"On Icon Clicked")
        actions_lay.addWidget(self.actions_combo)
        
        actions_lay.addWidget(QtWidgets.QLabel("Assigned Method:"))
        self.method_name = QtWidgets.QLabel("None")
        actions_lay.addWidget(self.method_name)

        self.main_layout.addLayout(actions_lay)

        methods_lay = QtWidgets.QHBoxLayout()
        methods_lay.setAlignment(QtCore.Qt.AlignLeft)

        methods_lay.addWidget(QtWidgets.QLabel("Methods available:"))
        self.methods_combo = QtWidgets.QComboBox()
        methods_lay.addWidget(self.methods_combo)
        if self.script_code:
            self.methods_combo.addItems([v for v in self.script_code.iterkeys()])
        self.methods_combo.addItem(QtGui.QIcon(ICONS + "add.svg"), "Create")
        self.methods_combo.addItem(QtGui.QIcon(ICONS + "close.svg"), "None")

        edit_methodname_btn = QtWidgets.QPushButton("")
        edit_methodname_btn.setFixedHeight(32)
        edit_methodname_btn.setFixedWidth(32)
        edit_methodname_btn.setIcon(QtGui.QIcon(ICONS + "edit.svg"))
        edit_methodname_btn.setIconSize(QtCore.QSize(25, 25))
        edit_methodname_btn.setToolTip("Edit method name")
        methods_lay.addWidget(edit_methodname_btn)

        apply_method_btn = QtWidgets.QPushButton("")
        apply_method_btn.setFixedHeight(32)
        apply_method_btn.setFixedWidth(32)
        apply_method_btn.setIcon(QtGui.QIcon(ICONS + "publish.svg"))
        apply_method_btn.setIconSize(QtCore.QSize(25, 25))
        apply_method_btn.setToolTip("Apply method to selected action.")
        methods_lay.addWidget(apply_method_btn)

        save_method_code_btn = QtWidgets.QPushButton("")
        save_method_code_btn.setFixedHeight(32)
        save_method_code_btn.setFixedWidth(32)
        save_method_code_btn.setIcon(QtGui.QIcon(ICONS + "save.svg"))
        save_method_code_btn.setIconSize(QtCore.QSize(25, 25))
        save_method_code_btn.setToolTip("Save method code.")
        methods_lay.addWidget(save_method_code_btn)

        delete_method_btn = QtWidgets.QPushButton("")
        delete_method_btn.setFixedHeight(32)
        delete_method_btn.setFixedWidth(32)
        delete_method_btn.setIcon(QtGui.QIcon(ICONS + "close.svg"))
        delete_method_btn.setIconSize(QtCore.QSize(25, 25))
        delete_method_btn.setToolTip("Delete method.")
        methods_lay.addWidget(delete_method_btn)

        self.main_layout.addLayout(methods_lay)
        
        self.code_editor = CodeEditor()
        self.main_layout.addWidget(self.code_editor)
        self.update_selected_code()
        self.methods_combo.currentIndexChanged.connect(self.update_selected_code)

        self.setLayout(self.main_layout)

    def update_selected_code(self):

        cur_sel = self.methods_combo.currentText()

        if cur_sel == "None":
            self.code_editor.setEnabled(False)
            self.code_editor.setPlainText("")
            return

        raw_code = self.script_code.get(cur_sel, "")
        raw_code = raw_code.split('\n')
        if raw_code[0].strip() == '':
            raw_code.pop(0)
        self.code_editor.setPlainText('\n'.join(raw_code))     

class PluginManager(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(PluginManager, self).__init__(parent=parent)

        self.setProperty("houdiniStyle", True)
        self.setWindowTitle("Plugin Manager")

        self.plugins = {}

        cw = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.plugin_infos_layout = QtWidgets.QVBoxLayout()
        self.plugin_infos_layout.setAlignment(QtCore.Qt.AlignTop)

        self.plugin_familly = PluginEntries(self)
        main_layout.addWidget(self.plugin_familly)
        main_layout.addLayout(self.plugin_infos_layout)

        cw.setLayout(main_layout)
        self.setCentralWidget(cw)

    def display_file_infos(self, name, infos):

        for w in self.plugins.itervalues():
            w.setVisible(False)

        if not name in self.plugins.keys():
            p = PluginInfos(infos, self)
            self.plugins[name] = p
            self.plugin_infos_layout.addWidget(p)
        else:
            self.plugins[name].setVisible(True)
            