import json
import os
import sys
import imp
from CirrusCore.cirrus_logger import Logger
from CirrusCore.cirrus_plugin_errors import *
from CirrusCore.cirrus_io import get_object_key
from CirrusCore.cirrus_connection import ConnectionInfos

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
            return m(path=kwargs["path"],
                     cloud_path=get_object_key(kwargs["path"]),
                     local_root=ConnectionInfos.get("local_root")[0:-1])

        Logger.Log.warn("Plugin failed, module {} doesn't have method {}".format(self._module,
                                                                                 self._on_get))
        return None

    def exec_on_save(self, *args, **kwargs):

        if not self._on_save:
            return None

        m = getattr(self._module, self._on_save, None)
        if m:
            return m(path=kwargs["path"],
                     cloud_path=get_object_key(kwargs["path"]),
                     local_root=ConnectionInfos.get("local_root")[0:-1])

        Logger.Log.warn("Plugin failed, module {} doesn't have method {}".format(self._module,
                                                                                 self._on_save))
        return None

    def exec_on_lock(self, *args, **kwargs):

        if not self._on_lock:
            return None

        m = getattr(self._module, self._on_lock, None)
        if m:
            return m(path=kwargs["path"],
                     cloud_path=get_object_key(kwargs["path"]),
                     local_root=ConnectionInfos.get("local_root")[0:-1])

        Logger.Log.warn("Plugin failed, module {} doesn't have method {}".format(self._module,
                                                                                 self._on_lock))
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