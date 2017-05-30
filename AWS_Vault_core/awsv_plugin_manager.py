import os
import sys

from PySide2 import QtGui
from PySide2 import QtCore
from PySide2 import QtWidgets

from AWS_Vault_core import awsv_plugin_parser
reload(awsv_plugin_parser)

from AWS_Vault_core import awsv_plugin_settings
reload(awsv_plugin_settings)

from AWS_Vault_core import py_highlighter
reload(py_highlighter)

ICONS          = os.path.dirname(__file__) + "\\icons\\"
PLUGINS_FOLDER = os.path.dirname(__file__) + "\\plugins\\"

class PluginEntries(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(PluginEntries, self).__init__(parent=parent)

        self.plugin_manager = parent

        self.plugin_settings = awsv_plugin_settings.PluginSettings()
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

        self.plugins_combo.currentIndexChanged.connect(self.update_selected_plugin)
        self.update_selected_plugin()

        self.selected_familly = self.plugins_combo.currentText()

    def update_selected_plugin(self):

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
        
        self.unsaved_changes = False

        self.setStyleSheet("background-color: #161616")
        py_highlighter.PythonHighlighter(self.document())

    def keyPressEvent(self, e):
        
        self.unsaved_changes = True

        # change tab to 4 spaces
        if e.key() == QtCore.Qt.Key_Tab:
            e = QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                QtCore.Qt.Key_Tab,
                                QtCore.Qt.KeyboardModifier.NoModifier,
                                text="    ")
            e.accept()
        super(CodeEditor, self).keyPressEvent(e)

    def get_code(self, indent_level=4):

        out = ['\n']
        out += [' ' * indent_level + line + '\n' for line \
                in self.toPlainText().split('\n')]
        if out[-1] != '    \n':
            out.append('    \n')
        return out

class OnIconMenuEntries(QtWidgets.QFrame):

    def __init__(self, parent=None):
        super(OnIconMenuEntries, self).__init__(parent=parent)
        self.entries = {}

        self.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
        self.setLineWidth(1)
        
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)

        add_entry_btn = QtWidgets.QPushButton("Add Menu Entry")
        add_entry_btn.clicked.connect(self.append_entry)
        main_layout.addWidget(add_entry_btn)

        self.entries_layout = QtWidgets.QVBoxLayout()
        self.entries_layout.setSpacing(2)
        self.entries_layout.setAlignment(QtCore.Qt.AlignTop)
        main_layout.addLayout(self.entries_layout)

        self.setLayout(main_layout)

    def remove_entry(self, w):

        w_name = w.name

        self.entries_layout.removeWidget(w)
        w.setParent(None)
        w.deleteLater()
        if w_name in self.entries.keys():
            del self.entries[w_name]

    def append_entry(self, method="", name=""):

        if name in self.entries.keys():
            return

        w = _OnIconMenuEntry(name=name,
                             method=method,
                             parent=self)
        self.entries_layout.addWidget(w)
        if name != "":
            self.entries[name] = w

class _OnIconMenuEntry(QtWidgets.QWidget):

    def __init__(self, name="", method="", parent=None):
        super(_OnIconMenuEntry, self).__init__(parent=parent)

        self.name = name

        self.top_ui = parent
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignLeft)

        self.name_input = QtWidgets.QLineEdit(name)
        self.name_input.setStyleSheet("background-color: transparent")
        main_layout.addWidget(self.name_input)

        a =QtWidgets.QLabel("")
        a.setPixmap(QtGui.QIcon(ICONS + "arrow_right.svg").pixmap(22, 22))
        main_layout.addWidget(a)

        self.method_input = QtWidgets.QComboBox()
        main_layout.addWidget(self.method_input)

        del_btn = QtWidgets.QPushButton("")
        del_btn.setIcon(QtGui.QIcon(ICONS + "close.svg"))
        del_btn.setFixedWidth(22)
        del_btn.setFixedHeight(22)
        del_btn.setFlat(True)
        del_btn.setIconSize(QtCore.QSize(22, 22))
        del_btn.clicked.connect(self.remove_me)
        main_layout.addWidget(del_btn)

        main_layout.setContentsMargins(0,0,0,0)
        self.setLayout(main_layout)

    def remove_me(self):

        self.top_ui.remove_entry(self)

class FileBindingsInput(QtWidgets.QDialog):

    def __init__(self, values, parent=None):
        super(FileBindingsInput, self).__init__(parent=parent)

        self.setWindowTitle("Edit file bindings")

        self.validated = False
        self.entries_values = values

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)

        entries_layout = QtWidgets.QHBoxLayout()
        entries_layout.setAlignment(QtCore.Qt.AlignLeft)

        entries_layout.addWidget(QtWidgets.QLabel("Entries (separated by a coma ','):"))
        self.entries = QtWidgets.QLineEdit(values)
        entries_layout.addWidget(self.entries)
        main_layout.addLayout(entries_layout)

        btn_layout = QtWidgets.QHBoxLayout()

        valid_btn = QtWidgets.QPushButton("Ok")
        valid_btn.setIcon(QtGui.QIcon(ICONS + "checkmark.svg"))
        valid_btn.setIconSize(QtCore.QSize(22, 22))
        valid_btn.clicked.connect(self.valid)
        btn_layout.addWidget(valid_btn)

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.setIcon(QtGui.QIcon(ICONS + "close.svg"))
        cancel_btn.setIconSize(QtCore.QSize(22, 22))
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)

        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def valid(self):

        self.validated = True
        self.entries_values = self.entries.text()
        self.close()

class PluginInfos(QtWidgets.QWidget):

    def __init__(self, plugin_infos, parent=None):
        super(PluginInfos, self).__init__(parent=parent)

        self.unsaved_changes = False
        self.plugin_manager = parent

        self.plugin_infos = plugin_infos
        self.bindings = {}
        self.methods = {}
        self.script_code = self.plugin_infos.script_code
        self.creating_new_method = False
        self.cur_selected_method = ""

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
        edit_files_btn.clicked.connect(self.edit_file_bindings)
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
        self.actions_combo.currentIndexChanged.connect(self.update_selected_action)
        actions_lay.addWidget(self.actions_combo)
        
        self.main_layout.addLayout(actions_lay)

        self.assigned_method_name = QtWidgets.QLabel("Assigned Method: None")
        self.main_layout.addWidget(self.assigned_method_name)

        self.menu_entries = OnIconMenuEntries(parent=self)
        self.menu_entries.setVisible(False)
        self.main_layout.addWidget(self.menu_entries)

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
        apply_method_btn.clicked.connect(self.apply_method)
        methods_lay.addWidget(apply_method_btn)

        save_method_code_btn = QtWidgets.QPushButton("")
        save_method_code_btn.setFixedHeight(32)
        save_method_code_btn.setFixedWidth(32)
        save_method_code_btn.setIcon(QtGui.QIcon(ICONS + "save.svg"))
        save_method_code_btn.setIconSize(QtCore.QSize(25, 25))
        save_method_code_btn.setToolTip("Save method code.")
        save_method_code_btn.clicked.connect(self.save_method_code)
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
        self.methods_combo.currentIndexChanged.connect(self.update_selected_method)

        self.save_plugin_btn = QtWidgets.QPushButton("Save Current Plugin")
        self.save_plugin_btn.setIcon(QtGui.QIcon(ICONS + "save.svg"))
        self.save_plugin_btn.setIconSize(QtCore.QSize(22, 22))
        self.save_plugin_btn.clicked.connect(self.save_plugin)
        self.main_layout.addWidget(self.save_plugin_btn)

        self.update_selected_action()
        self.update_selected_method()

        self.setLayout(self.main_layout)

    def edit_file_bindings(self):
        
        cur = self.file_bindins_combo.currentText()
        w = FileBindingsInput(cur, self)
        w.exec_()
        if w.entries_values != cur and w.validated:
            self.toggle_unsaved_changes()

            cur_binding_uid = self.bindings[cur]
            self.bindings[w.entries_values] = cur_binding_uid
            del self.bindings[cur]

            binding = [b for b in self.plugin_infos.bindings \
                       if b.uid == cur_binding_uid][0]
            binding.files = w.entries_values.replace(' ', '').split(',')

    def create_method(self):

        if self.creating_new_method: return

        meth_name, ok = QtWidgets.QInputDialog.getText(self, 'Enter Name', 'Enter method name')
        if ok:
            if meth_name.lower() in ["create", "none"]:
                QtWidgets.QMessageBox.critical(self, "Error", "Invalid method name")
                self.methods_combo.setCurrentText(self.cur_selected_method)
                return

            if meth_name in self.script_code.keys():
                QtWidgets.QMessageBox.critical(self, "Error", "Method with this name already exist")
                self.methods_combo.setCurrentText(self.cur_selected_method)
                return

            self.creating_new_method = True
            meth_name = meth_name.replace(' ', '_')
            self.methods_combo.insertItem(0, meth_name)
            self.methods_combo.setCurrentText(meth_name)
            self.cur_selected_method = meth_name

            default_code = """# Write your method code here
# A 'kwargs' dict is available with these entries:
# kwargs["path"] => local file path
# kwargs["cloud_path"] => file path on the cloud
# kwargs["local_root"] => the current project's root folder

file_path = kwargs["path"]"""
            self.code_editor.setPlainText(default_code)
            self.script_code[meth_name] = default_code
            self.creating_new_method = False
            self.toggle_unsaved_changes()
        else:
            self.methods_combo.setCurrentText(self.cur_selected_method)

    def apply_method(self):
        
        action = self.actions_combo.currentText().lower().replace(' ', '_')
        cur_binding = self.file_bindins_combo.currentText()
        methods = self.methods.get(cur_binding)
        cur_method = self.methods_combo.currentText()

        msg = "Apply method: '{}' to action: '{}' ?".format(cur_method, action)
        r = QtWidgets.QMessageBox.information(self,
                                              "Confirm", msg,
                                              "Yes", "Cancel")
        if r == 1: return

        if cur_method == "None":
            methods.set(action, None)
        else:
            methods.set(action, cur_method)
        self.assigned_method_name.setText("Assigned Method: " + cur_method)
        self.toggle_unsaved_changes()

    def update_selected_method(self):

        if self.creating_new_method: return

        if self.code_editor.unsaved_changes:

            r = QtWidgets.QMessageBox.question(self, "Unsaved changes",
                                           "Save current code ?",
                                           "Yes", "No, Discard unsaved changes", "Cancel")
            if r == 2:
                self.methods_combo.setCurrentText(self.cur_selected_method)
                return

            elif r == 0:
                self.save_method_code(self.cur_selected_method, False)

            self.code_editor.unsaved_changes = False

        cur_sel = self.methods_combo.currentText()

        if cur_sel == "None":
            self.code_editor.setEnabled(False)
            self.code_editor.setPlainText("")
            return

        if cur_sel == "Create":
            if self.creating_new_method:
                return
            self.create_method()
        
        cur_sel = self.methods_combo.currentText()
        raw_code = self.script_code.get(cur_sel, "")
        raw_code = raw_code.split('\n')
        if raw_code[0].strip() == '':
            raw_code.pop(0)
        self.code_editor.setPlainText('\n'.join(raw_code))
        self.cur_selected_method = cur_sel

    def update_selected_action(self):

        cur_binding = self.file_bindins_combo.currentText()
        cur_act = self.actions_combo.currentText().replace(' ', '_').lower()
        methods = self.methods.get(cur_binding)
        cur_meth = methods.get(cur_act)

        if cur_act == "on_icon_clicked":
            self.menu_entries.setVisible(True)
            self.assigned_method_name.setText("Assigned Method: Menu")
            if cur_meth:
                for k, v in cur_meth.iteritems():
                    self.menu_entries.append_entry(k, v)
        else:
            self.menu_entries.setVisible(False)
            if cur_meth:
                self.assigned_method_name.setText("Assigned Method: " + cur_meth)
            else:
                self.assigned_method_name.setText("Assigned Method: None")

    def save_method_code(self, selected_method=None, ask=True):

        script_file = PLUGINS_FOLDER + self.plugin_infos.script
        assert os.path.exists(script_file), "script file not found: " + script_file

        if ask:
            r = QtWidgets.QMessageBox.information(self,
                                              "Confirm", "Save current method code ?",
                                              "Yes", "Cancel")
            if r == 1: return
        
        if not selected_method:
            selected_method = self.methods_combo.currentText()

        with open(script_file, 'r') as f:
            raw_data = f.readlines()

        if not "def " + selected_method + "(**kwargs):\n" in raw_data:
            # append code to file
            code = ["\n\ndef " + selected_method + "(**kwargs):\n"]
            code += self.code_editor.get_code()
            with open(script_file, 'a') as f:
                f.writelines(code)

        else:
            # replace code in file
            code = []
            in_method = False
            new_code_appened = False
            for i, c in enumerate(raw_data):

                if c == "def " + selected_method + "(**kwargs):\n":
                    in_method = True

                elif c.startswith("def") and c.endswith("(**kwargs):\n"):
                    in_method = False
               
                if not in_method:
                    code.append(c)
                else:
                    if new_code_appened:
                        continue

                    code += ["def " + selected_method + "(**kwargs):\n"]
                    code += self.code_editor.get_code()
                    new_code_appened = True

            with open(script_file, 'w') as f:
                f.writelines(code)

            self.code_editor.unsaved_changes = False

    def save_plugin(self):

        msg = "Save plugin: " + self.plugin_infos.plugin_name + " ?"
        r = QtWidgets.QMessageBox.information(self,
                                              "Confirm", msg,
                                              "Yes", "Cancel")
        if r == 1: return

        self.plugin_infos.plugin_settings.save(self.plugin_infos.plugin_name)
        QtWidgets.QMessageBox.information(self, "Info", "Plugin saved !")
        self.toggle_unsaved_changes(False)

    def toggle_unsaved_changes(self, toggle=True):

        self.unsaved_changes = toggle
        if toggle:
            self.plugin_manager.setWindowTitle("Plugin Manager (unsaved changes)")
        else:
            self.plugin_manager.setWindowTitle("Plugin Manager")

class PluginManager(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(PluginManager, self).__init__(parent=parent)

        self.setProperty("houdiniStyle", True)
        self.setWindowTitle("Plugin Manager")
        self.setWindowIcon(QtGui.QIcon(ICONS + "plugin.svg"))

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
            