import json
import os
import sys
import imp
import uuid
import logging
from AWS_Vault_core.awsv_logger import Logger

from PySide2 import QtWidgets

"""
    Plugin are python scripts executed after certain actions:
     "on_get" will be executed after the user downloaded a file from cloud.
     "on_lock" will be executed after the user locked a file.
     "on_save" will be executed before the user save a file to the cloud.
     "on_icon_clicked" generates a QMenu according to the methods definied.
                       the menu will pop up when the user click on the file's icon.
"""

plugin_settings = os.path.dirname(__file__) + os.sep + "plugins" + os.sep + "plugin_settings.json"
plugins_scripts = os.path.dirname(__file__) + os.sep + "plugins"
EXE = sys.executable

class PluginFileNotFoundError(Exception):
    """ Raised if a given plugin file ( python ) is not found under the plugins folder
    """
    pass

class InvalidPluginFileMethodAlreadyExistError(Exception):
    """ Raise when two methods with the same name exist in a plugin file
    """
    pass

class InvalidPluginSettingsError(Exception):
    """ Raised when an error is found in plugin_settings.json formatting
    """
    pass

class InvalidGetMethodError(Exception):
    """ Raised when the get() method of PluginInfos is used with invalid arguments
    """
    pass

class PluginRepository():

    VALID_FILES = []
    PLUGINS = []

class Plugin(object):

    __slots__ = ["script_path", "files",
                 "_on_get", "_on_save", "_on_lock",
                 "_on_icon_clicked", "_module"]

    def __init__(self, script_path=""):

        self.script_path = script_path
        self.files = []
        self._on_get = None
        self._on_save = None
        self._on_lock = None
        self._on_icon_clicked = None
        self._module = None

    def __str__(self):

        out = ""
        out += "Script path: " + self.script_path
        return out

    def __repr__(self):
        return self.__str__()

    def exec_on_get(self, *args, **kwargs):

        if not self._on_get:
            return None

        m = getattr(self._module, self._on_get, None)
        if m:
            return m(path=kwargs["path"])

        Logger.Log.warn("Plugin failed, module {} doesn't have method {}".format(self._module, self._on_get))
        return None

    def exec_on_save(self, *args, **kwargs):

        if not self._on_save:
            return None

        m = getattr(self._module, self._on_save, None)
        if m:
            return m(args, kwargs)

        Logger.Log.warn("Plugin failed, module {} doesn't have method {}".format(self._module, self._on_save))
        return None

    def exec_on_lock(self, *args, **kwargs):

        if not self._on_lock:
            return None

        m = getattr(self._module, self._on_lock, None)
        if m:
            return m(args, kwargs)

        Logger.Log.warn("Plugin failed, module {} doesn't have method {}".format(self._module, self._on_lock))
        return None

    def on_icon_clicked_menu(self, parent, **kwargs):

        if not self._on_icon_clicked:
            return None

        menu = QtWidgets.QMenu(parent=parent)
        valid_act = 0
        for k, v in self._on_icon_clicked.iteritems():
            m = getattr(self._module, k, None)
            if not m:
                Logger.Log.warn("Plugin failed, module {} doesn't have method {}".format(self._module, k))
                continue
            act = QtWidgets.QAction(v, parent)
            act.triggered.connect(lambda v=m: v(path=kwargs["path"],
                                                local_root=kwargs["local_root"],
                                                cloud_path=kwargs["cloud_path"]))
            menu.addAction(act)
            valid_act += 1

        if valid_act == 0:
            return None

        return menu

class PluginSettingInfo():

    def __init__(self, inf):

        self.enable = inf.get("enable", False)
        self.plugin_name = inf.get("plugin_name")
        self.software_executable = inf.get("software_executable")
        self.script = inf.get("script")
        self.bindings = [_PluginFileBindings(_inf) for _inf in inf.get("bindings")]
        self.script_code = self.parse_plugin_code(self.script)

    def get_plugin_name(self):

        return self.plugin_name

    def get_plugin_exe(self):

        return self.software_executable

    def parse_plugin_code(self, file):
        """ Parse source code of a given file and return methodes names + code
        """

        plugin_path = plugins_scripts + os.sep + file
        if not os.path.exists(plugin_path):
            return None

        with open(plugin_path, 'r') as f:
            data = f.readlines()

        methodes = {}
        cur_method = ""

        for i, line in enumerate(data):

            if line.startswith("def ") and line.endswith("(**kwargs):\n"):
                line = line.replace("def ", "").replace("(**kwargs):\n", "")
                if line in methodes.keys():
                    raise InvalidPluginFileMethodAlreadyExistError(plugin_path + " line: " + str(i))

                methodes[line] = ""
                cur_method = line
                continue

            else:
                if cur_method != "":
                    methodes[cur_method] += line.replace('    ', '', 1)

        return methodes

    def _get_result(self, obj, attrs):

        if len(attrs) == 1:
            return getattr(obj, attrs[0], None)
        else:
            return [getattr(obj, a, None) for a in attrs]

    def get(self, attr, level=None, uid=""):

        attrs = attr.replace(' ', '').split(',')

        if level is None:
            return self._get_result(self, attrs)

        if level == "bindings":
            b = self.get_bindings(uid)
            if not b:
                return None
            if uid != "":
                return self._get_result(b[0], attrs)
                
            return [self._get_result(n, attrs) for n in b]

    def get_bindings(self, uid=""):
        
        if uid != "":
            return [b for b in self.bindings if b.uid == uid]

        return self.bindings

class _PluginFileBindings():

    def __init__(self, inf):

        self.uid = inf.get("uid")
        self.files = inf.get("files")
        self.methods = _PluginBindingMethods(inf.get("methods"))

class _PluginBindingMethods():

    def __init__(self, kwargs):

        self.on_get = kwargs.get("on_get")
        self.on_save = kwargs.get("on_save")
        self.on_lock = kwargs.get("on_lock")
        self.on_icon_clicked = kwargs.get("on_icon_clicked")

class PluginSettings():
    """ Object which saves the data parsed from the plugin_settings.json
        
        An attribute can be get using the methode get(attr, [level], [uid], [plugin_name]) following this:

        attr => attr1,attr2,... attributes you want to get
        optional level => binding or methods to set which level of data you want to get, is left blank the
                          level will be set to plugin itself ( highest level ).
        optional uid => for binding level only, set a specific binding uid, if left blank a list of results
                        will be resturn for each bindind found.
        optional plugin_name => can be used when level is left blank, to get data from a specific plugin.
        
    """
    def __init__(self):

        self.setting_data = None
        self.plugins = []
        self.read_settings()

    def read_settings(self):

        with open(plugin_settings) as data:
            plugin_data = json.load(data)
        self.setting_data = plugin_data

        for p in self.setting_data["plugins"]:
            self.plugins.append(PluginSettingInfo(p))

        return plugin_data

    def _generate_uuid():

        return str(uuid.uuid4())
    
    def get(self, attr, level=None, uid="", plugin_name=""):

        if level is not None and plugin_name != "":
            raise InvalidGetMethodError()

        if plugin_name == "":
            return [p.get(attr, level, uid) for p in self.plugins]

        return [p.get(attr, level, uid) for p in self.plugins \
                if p.get_plugin_name() == plugin_name][0]


def get_plugin_files_filter(plugin_name):

    return

def get_plugin():
    """ Parse and get valid plugins for current app
    """
    PluginRepository.PLUGINS = []
    PluginRepository.VALID_FILES = []

    root, f = os.path.split(EXE)
    software_key = f.split('.', 1)[0]

    Logger.Log.info("Parsing plugins, software key: " + software_key)

    with open(plugin_settings) as data:
        plugin_data = json.load(data)
    
    plugins = plugin_data.get("plugins")
    if not plugins:
        Logger.Log.warning("plugin_settings.json not valid, 'plugins' key not found")
        return

    valid_plugin = None
    for plugin in plugins:

        if not plugin["enable"]: continue

        if software_key in plugin["software_executable"]:
            valid_plugin = plugin
            break

    if not valid_plugin:
        Logger.Log.warning("No valid plugin found for given software_key")
        return

    script_path = plugins_scripts + os.sep + valid_plugin["script"]
    if not os.path.exists(script_path):
        Logger.Log.warning("Plugin script path not valid: " + script_path)
        return

    valid_plugins = []
    valid_files = []
    for i, bindings in enumerate(valid_plugin["bindings"]):

        if not bindings["files"]:
            Logger.Log.warning("Plugin {} invalid 'files'.".format(i))
            continue

        p = Plugin()
        p.files = bindings["files"]
        valid_files += bindings["files"]
        methods = bindings["methods"]
        
        p._on_get = methods["on_get"]
        p._on_save = methods["on_save"]
        p._on_lock = methods["on_lock"]
        p._on_icon_clicked = methods["on_icon_clicked"]

        p._module = imp.load_source(software_key + str(i), script_path)

        valid_plugins.append(p)
    
    if not valid_plugins:
        return

    Logger.Log.info(str(len(valid_plugins)) + " Plugin(s) loaded")

    PluginRepository.PLUGINS = valid_plugins
    PluginRepository.VALID_FILES = valid_files