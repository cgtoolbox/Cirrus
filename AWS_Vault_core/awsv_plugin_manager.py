import os
import itertools
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

from AWS_Vault_core.awsv_logger import Logger

ICONS          = os.path.dirname(__file__) + "\\icons\\"
PLUGINS_FOLDER = os.path.dirname(__file__) + "\\plugins\\"

class MethodListModel(QtCore.QAbstractListModel):

    def __init__(self, methods=[], parent=None):
        super(MethodListModel, self).__init__(parent=parent)
        self.__methods = methods

    def rowCount(self, parent):

        return len(self.__methods)

    def data(self, index, role):

        r = index.row()
        val = self.__methods[r]

        if role == QtCore.Qt.ToolTipRole:

            if val == "Create":
                return "Create a new method"

            if val == "None":
                return "Set the current method to None"

            return "Method '" + val + "' code."

        if role == QtCore.Qt.DecorationRole:

            if val == "Create":
                ico = QtGui.QIcon(ICONS + "add.svg")
                return ico

            if val == "None":
                ico = QtGui.QIcon(ICONS + "close.svg")
                return ico

            ico = QtGui.QIcon(ICONS + "arrow_right.svg")
            return ico

        if role == QtCore.Qt.DisplayRole:
            return val

    def insertRows(self, position, rows=1, parent=QtCore.QModelIndex(), value=""):

        self.beginInsertRows(QtCore.QModelIndex(),
                             position, position + rows - 1)

        for i in range(rows):
            self.__methods.insert(position, value)

        self.endInsertRows()

    def removeRows(self, position=0, rows=1, parent=QtCore.QModelIndex(), value=""):

        idx = self.__methods.index(value)
        self.beginRemoveRows(parent, idx, idx)
        self.__methods.pop(idx)
        self.endRemoveRows()
        return True

class PluginEntries(QtWidgets.QWidget):

    def __init__(self, plugin_settings, parent=None):
        super(PluginEntries, self).__init__(parent=parent)

        self.plugin_manager = parent

        self.plugin_settings = plugin_settings
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

        if self._adding_item: return

        if self.plugins_combo.currentText() == "Create":

            plug_name, ok = QtWidgets.QInputDialog.getText(self, 'Enter Name', 'Enter plugin name')
            if ok:
                self._adding_item = True
                c = self.plugins_combo.count()
                self.plugins_combo.insertItem(0, plug_name)
                self.plugins_combo.setCurrentIndex(0)
                self.p_fam_executables.setText("")
                self.plugin_manager.add_plugin(plug_name)
                self.plugins_combo.setCurrentText(plug_name)
                self.selected_familly = plug_name
            else:
                self.plugins_combo.setCurrentText(self.selected_familly)

            self._adding_item = False
            return

        cur = self.plugins_combo.currentText()
        if cur == "Create":
            cur = self.selected_familly

        selected_plugin = [n for n in self.plugins \
            if n.get_plugin_name() == cur][0]

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

    def __init__(self, model, parent=None):
        super(OnIconMenuEntries, self).__init__(parent=parent)
        self.entries = {}
        self.model = model

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
                             model=self.model,
                             method=method,
                             parent=self)
        self.entries_layout.addWidget(w)
        if name != "":
            self.entries[name] = w

class _OnIconMenuEntry(QtWidgets.QWidget):

    def __init__(self, name="", model=None, method="", parent=None):
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
        self.method_input.setModel(model)
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

class MethodDeletionWarning(QtWidgets.QDialog):

    def __init__(self, data, parent=None):
        super(MethodDeletionWarning, self).__init__(parent=parent)

        self.VALID = False

        self.setWindowTitle("Warning")
        main_layout = QtWidgets.QVBoxLayout()

        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.setAlignment(QtCore.Qt.AlignLeft)

        risk = QtWidgets.QLabel("")
        risk.setPixmap(QtGui.QIcon(ICONS + "risk.svg").pixmap(64,64))
        risk.setFixedWidth(64)
        risk.setFixedHeight(64)
        sub_layout.addWidget(risk)

        warning_layout = QtWidgets.QVBoxLayout()
        warning_layout.setAlignment(QtCore.Qt.AlignTop)
        warning_layout.addWidget(QtWidgets.QLabel("One or more bindings use this method !"))
        warning_layout.addWidget(QtWidgets.QLabel("Binding(s) involved:"))

        for k, v in data.iteritems():

            _lay = QtWidgets.QHBoxLayout()
            
            _lbl = QtWidgets.QLabel("")
            _lbl.setContentsMargins(15, 0, 0, 0)
            _lbl.setPixmap(QtGui.QIcon(ICONS + "white_list.svg").pixmap(24, 24))
            _lbl.setFixedWidth(39)

            _lay.addWidget(_lbl)
            _lay.addWidget(QtWidgets.QLabel(k))

            warning_layout.addLayout(_lay)

            _lay2 = QtWidgets.QHBoxLayout()
            
            _lbl2 = QtWidgets.QLabel("")
            _lbl2.setContentsMargins(30, 0, 0, 0)
            _lbl2.setPixmap(QtGui.QIcon(ICONS + "arrow_right.svg").pixmap(16, 16))
            _lbl2.setFixedWidth(46)

            _lay2.addWidget(_lbl2)
            _lay2.addWidget(QtWidgets.QLabel(', '.join(v[1:])))

            warning_layout.addLayout(_lay2)
            warning_layout.addWidget(QtWidgets.QLabel(""))

        sub_layout.addLayout(warning_layout)
        main_layout.addLayout(sub_layout)

        btn_layout = QtWidgets.QHBoxLayout()
        self.accept_btn = QtWidgets.QPushButton("Yes, Delete Method")
        self.accept_btn.setIcon(QtGui.QIcon(ICONS + "checkmark.svg"))
        self.accept_btn.setIconSize(QtCore.QSize(26, 26))
        self.accept_btn.clicked.connect(self.valid_act)
        btn_layout.addWidget(self.accept_btn)

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setIcon(QtGui.QIcon(ICONS + "close.svg"))
        self.cancel_btn.setIconSize(QtCore.QSize(26, 26))
        self.cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

    def valid_act(self):

        self.VALID = True
        self.close()

class FileBindingsInput(QtWidgets.QDialog):

    def __init__(self, values, parent=None, existing_entries=[]):
        super(FileBindingsInput, self).__init__(parent=parent)

        self.setWindowTitle("Edit file bindings")

        self.validated = False
        self.entries_values = values
        self.existing_entries = existing_entries

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

        if self.existing_entries:
            
            cur = self.entries.text().replace(' ', '').split(',')
            invalid_entires = [n for n in cur if n in self.existing_entries]
            if invalid_entires:
                msg = "Files already used in another binding:\n"
                msg += ','.join(invalid_entires)
                QtWidgets.QMessageBox.critical(self, "Error", msg)
                return

        self.validated = True
        clean_entires = ", ".join(self.entries.text().replace(' ', '').split(','))
        self.entries_values = clean_entires
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
        self.creating_binding = False
        self.cur_selected_method = ""

        r = self.plugin_infos.get("files,uid", level="bindings")
        if r:
            for files, uid in r:
                self.bindings[', '.join(files)] = uid
                self.methods[', '.join(files)] = self.plugin_infos.get("methods", level="bindings", uid=uid)

        # methods available data
        li = []
        if self.script_code:
            li = [v for v in self.script_code.iterkeys()]
            li.append("Create")
            li.append("None")
        else:
            li = ["Create", "None"]
        self.method_list = MethodListModel(methods=li)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.file_bindings_lay = QtWidgets.QHBoxLayout()
        self.file_bindings_lay.setAlignment(QtCore.Qt.AlignLeft)
        self.file_bindings_lay.addWidget(QtWidgets.QLabel("File Bindings:"))

        self.file_bindings_combo = QtWidgets.QComboBox()
        self.file_bindings_combo.addItems([v for v in self.bindings.iterkeys()])
        self.file_bindings_combo.addItem(QtGui.QIcon(ICONS + "add.svg"), "Create")
        self.file_bindings_combo.currentIndexChanged.connect(self.update_selected_binding)
        self.file_bindings_lay.addWidget(self.file_bindings_combo)
        
        edit_files_btn = QtWidgets.QPushButton("")
        edit_files_btn.setFixedHeight(32)
        edit_files_btn.setFixedWidth(32)
        edit_files_btn.setIcon(QtGui.QIcon(ICONS + "edit.svg"))
        edit_files_btn.setIconSize(QtCore.QSize(25, 25))
        edit_files_btn.setToolTip("Edit files list")
        edit_files_btn.clicked.connect(self.edit_file_bindings)
        self.file_bindings_lay.addWidget(edit_files_btn)

        delete_files_bindings_btn = QtWidgets.QPushButton("")
        delete_files_bindings_btn.setFixedHeight(32)
        delete_files_bindings_btn.setFixedWidth(32)
        delete_files_bindings_btn.setIcon(QtGui.QIcon(ICONS + "close.svg"))
        delete_files_bindings_btn.setIconSize(QtCore.QSize(25, 25))
        delete_files_bindings_btn.setToolTip("Delete selected files binding.")
        delete_files_bindings_btn.clicked.connect(self.delete_files_binding)
        self.file_bindings_lay.addWidget(delete_files_bindings_btn)

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

        self.menu_entries = OnIconMenuEntries(self.method_list, parent=self)
        self.menu_entries.setVisible(False)
        self.main_layout.addWidget(self.menu_entries)

        methods_lay = QtWidgets.QHBoxLayout()
        methods_lay.setAlignment(QtCore.Qt.AlignLeft)

        methods_lay.addWidget(QtWidgets.QLabel("Methods available:"))
        self.methods_combo = QtWidgets.QComboBox()
        methods_lay.addWidget(self.methods_combo)
        self.methods_combo.setModel(self.method_list)

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
        delete_method_btn.clicked.connect(self.delete_method)
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

    def create_file_binding(self):

        exising_items = list(itertools.chain.from_iterable([n.files for \
                        n in self.plugin_infos.bindings]))

        w = FileBindingsInput("", self, existing_entries=exising_items)
        
        w.exec_()
        if w.validated:
            self.file_bindings_combo.insertItem(0, w.entries_values)
            self.file_bindings_combo.setCurrentIndex(0)
            uid = self.plugin_infos.plugin_settings._generate_uuid()
            infos = {"uid":uid,
                     "files":w.entries_values.replace(' ','').split(','),
                     "methods":{"on_get":None, "on_save":None,
                                "on_lock":None, "on_icon_clicked":[]}}
            new_b = awsv_plugin_settings._PluginFileBindings(infos, self)
            self.plugin_infos.bindings.append(new_b)
            self.methods[w.entries_values] = new_b.methods
            self.toggle_unsaved_changes()

    def edit_file_bindings(self):
        
        cur = self.file_bindings_combo.currentText()
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
            m = self.methods_combo.model()
            m.insertRows(0, value=meth_name)
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
            self.save_method_code(meth_name, False)
        else:
            self.methods_combo.setCurrentText(self.cur_selected_method)

    def apply_method(self):
        
        action = self.actions_combo.currentText().lower().replace(' ', '_')
        cur_binding = self.file_bindings_combo.currentText()
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

    def update_selected_binding(self):

        
        cur_binding = self.file_bindings_combo.currentText()
        if cur_binding == "Create" and not self.creating_binding:

            self.creating_binding = True
            r = self.create_file_binding()
            self.creating_binding = False
    
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

        cur_binding = self.file_bindings_combo.currentText()
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

    def delete_files_binding(self):

        cur = self.file_bindings_combo.currentText()

        r = QtWidgets.QMessageBox.question(self, "Confirm",
                                           "Delete files binding: " + cur + " ?")
        if r == QtWidgets.QMessageBox.No: return

        files = cur.replace(' ','').split(',')
        cur_bin = [b for b in self.plugin_infos.bindings if b.files == files]
        if cur_bin:
            cur_bin = cur_bin[0]
            self.plugin_infos.bindings.pop(self.plugin_infos.bindings.index(cur_bin))

        if cur in self.methods.keys():
            del self.methods[cur]

        idx = self.file_bindings_combo.findText(cur)
        self.file_bindings_combo.removeItem(idx)
        self.toggle_unsaved_changes()

    def delete_method(self):

        selected_method = self.methods_combo.currentText()

        r = QtWidgets.QMessageBox.question(self, "Confirm",
                                           "Delete the method: " + selected_method + " ?")
        if r == QtWidgets.QMessageBox.No: return

        Logger.Log.debug("Deleting method: " + selected_method)
        
        m = self.script_code.get(selected_method)
        if not m: return

        # check if any bindings use this method, if yes display a warning.
        # if the warning is ignored, set the binding methods to None.
        warning_bindings = {}
        for binding in self.plugin_infos.bindings:

            uid = binding.uid
            result = []
            on_get = self.plugin_infos.get("on_get", level="methods", uid=uid)
            if on_get == selected_method:
                result.append("on_get")

            on_lock = self.plugin_infos.get("on_lock", level="methods", uid=uid)
            if on_lock == selected_method:
                result.append("on_lock")

            on_save = self.plugin_infos.get("on_save", level="methods", uid=uid)
            if on_save == selected_method:
                result.append("on_save")

            on_icon_clicked = self.plugin_infos.get("on_icon_clicked", level="methods", uid=uid)
            if selected_method in on_icon_clicked.iterkeys():
                result.append("on_clicked")

            if result:
                result.insert(0, uid)
                warning_bindings[','.join(binding.files)] = result

        if warning_bindings != {}:

            r = MethodDeletionWarning(warning_bindings, self)
            r.exec_()
            if not r.VALID: return

            for r, v in warning_bindings.iteritems():

                uid = v[0]
                methods = v[1:]

                binding = self.plugin_infos.get_bindings(uid=uid)
                if not binding: continue

                for m in methods:

                    if m == "on_icon_clicked":
                        pass

                    else:
                        met = binding.methods
                        met.set(m, None)
            
            self.toggle_unsaved_changes()


        del self.script_code[selected_method]

        script_file = PLUGINS_FOLDER + self.plugin_infos.script
        with open(script_file, 'r') as f:
            raw_data = f.readlines()

        code = []
        in_method = False
        for i, c in enumerate(raw_data):

            if c == "def " + selected_method + "(**kwargs):\n":
                in_method = True
                continue

            elif c.startswith("def") and c.endswith("(**kwargs):\n") \
                and not selected_method in c:
                in_method = False

            if in_method: continue
               
            code.append(c)
        
        with open(script_file, 'w') as f:
            f.writelines(code)

        j = self.methods_combo.findText(selected_method)
        self.methods_combo.removeItem(j)

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

        self.plugin_settings = awsv_plugin_settings.PluginSettings()

        cw = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.plugin_infos_layout = QtWidgets.QVBoxLayout()
        self.plugin_infos_layout.setAlignment(QtCore.Qt.AlignTop)

        self.plugin_entries = PluginEntries(self.plugin_settings, self)
        main_layout.addWidget(self.plugin_entries)
        main_layout.addLayout(self.plugin_infos_layout)

        cw.setLayout(main_layout)
        self.setCentralWidget(cw)

    def add_plugin(self, plugin_name):
        
        script = PLUGINS_FOLDER + plugin_name + ".py"
        if os.path.exists(script):
            QtWidgets.QMessageBox.critical(self, "Error",
                                           "A plugin name " + plugin_name + " already exist.")
            return
        
        default_code = '''"""
WARNING: code generated by the awsv plugin manager, this code
         should not be edited manually.
"""
def example_method(**kwargs):

    # Write your method code here
    # A 'kwargs' dict is available with these entries:
    # kwargs["path"] => local file path
    # kwargs["cloud_path"] => file path on the cloud
    # kwargs["local_root"] => the current project's root folder

    file_path = kwargs["path"]'''

        with open(script, 'w') as f:
            f.write(default_code)
        
        infos = self.plugin_settings.add_plugin(plugin_name)
        self.plugin_settings.read_settings()
        self.plugin_entries.plugins = self.plugin_settings.plugins
        p = awsv_plugin_settings.PluginSettingInfo(infos, self)
        self.display_file_infos(plugin_name, p)

    def display_file_infos(self, name, infos):

        for w in self.plugins.itervalues():
            w.setVisible(False)

        if not name in self.plugins.keys():
            p = PluginInfos(infos, self)
            self.plugins[name] = p
            self.plugin_infos_layout.addWidget(p)
        else:
            self.plugins[name].setVisible(True)
            