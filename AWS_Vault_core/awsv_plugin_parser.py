import json
import os
import sys
import imp
import logging
log = logging.getLogger("root")

from PySide2 import QtWidgets

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

    def exec_on_get(self, *args, **kwargs):

        if not self._on_get:
            return None

        m = getattr(self._module, self._on_get, None)
        if m:
            log.warn("Plugin failed, exec_on_get, module {} doesn't have method {}".format(self._module, self._on_get))
            return m(path=kwargs["path"])
        return None

    def exec_on_save(self, *args, **kwargs):

        if not self._on_save:
            return None

        m = getattr(self._module, self._on_save, None)
        if m:
            log.warn("Plugin failed, exec_on_save, module {} doesn't have method {}".format(self._module, self._on_save))
            return m(args, kwargs)
        return None

    def exec_on_lock(self, *args, **kwargs):

        if not self._on_lock:
            return None

        m = getattr(self._module, self._on_lock, None)
        if m:
            log.warn("Plugin failed, exec_on_lock, module {} doesn't have method {}".format(self._module, self._on_lock))
            return m(args, kwargs)
        return None

    def on_icon_clicked_menu(self, parent, **kwargs):

        if not self._on_icon_clicked:
            return None

        menu = QtWidgets.QMenu(parent=parent)
        valid_act = 0
        for k, v in self._on_icon_clicked.iteritems():
            m = getattr(self._module, k, None)
            if not m:
                log.warn("Plugin failed, on_icon_clicked_menu, module {} doesn't have method {}".format(self._module, k))
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

def parse_plugin():

    PluginRepository.PLUGINS = []
    PluginRepository.VALID_FILES = []

    root, f = os.path.split(EXE)
    software_key = f.split('.', 1)[0]

    log.info("Parsing plugins, software key: " + software_key)

    with open(plugin_settings) as data:
        plugin_data = json.load(data)
    
    plugins = plugin_data.get("plugins")
    if not plugins:
        log.warning("plugin_settings.json not valid, 'plugins' key not found")
        return

    valid_plugin = None
    for plugin in plugins:

        if not plugin["enable"]: continue

        if software_key in plugin["software"]:
            valid_plugin = plugin
            break

    if not valid_plugin:
        log.warning("No valid plugin found for given software_key")
        return

    script_path = plugins_scripts + os.sep + valid_plugin["script"]
    if not os.path.exists(script_path):
        log.warning("Plugin script path not valid: " + script_path)
        return

    valid_plugins = []
    valid_files = []
    for i, binding in enumerate(valid_plugin["binding"]):

        if not binding["files"]:
            log.warning("Plugin {} invalid 'files'.".format(i))
            continue

        p = Plugin()
        p.files = binding["files"]
        valid_files += binding["files"]
        methods = binding["methods"]
        
        p._on_get = methods["on_get"]
        p._on_save = methods["on_save"]
        p._on_lock = methods["on_lock"]
        p._on_icon_clicked = methods["on_icon_clicked"]

        p._module = imp.load_source(software_key + str(i), script_path)

        valid_plugins.append(p)
    
    if not valid_plugins:
        return

    PluginRepository.PLUGINS = valid_plugins
    PluginRepository.VALID_FILES = valid_files