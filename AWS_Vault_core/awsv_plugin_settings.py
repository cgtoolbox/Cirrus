import json
import os
import sys
import imp
import uuid
import logging
from AWS_Vault_core.awsv_logger import Logger
from AWS_Vault_core.awsv_plugin_errors import *
from AWS_Vault_core import awsv_plugin_parser

plugin_settings = os.path.dirname(__file__) + os.sep + "plugins" + os.sep + "plugin_settings.json"
plugins_scripts = os.path.dirname(__file__) + os.sep + "plugins"
EXE = sys.executable

class PluginSettingInfo():

    def __init__(self, inf, plugin_settings):

        self.enable = inf.get("enable", False)
        self.plugin_name = inf.get("plugin_name")
        self.software_executable = inf.get("software_executable")
        self.script = inf.get("script")
        self.bindings = [_PluginFileBindings(_inf, self) for _inf in inf.get("bindings")]
        self.script_code = self.parse_plugin_code(self.script)
        self.plugin_settings = plugin_settings

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

    def get_data_tree(self):

        data = {}
        data["enable"] = self.enable
        data["plugin_name"] = self.plugin_name
        data["software_executable"] = self.software_executable
        data["script"] = self.script
        data["bindings"] = [b.get_date_tree() for b in self.bindings]
        return data

    def save(self):
        # save the current plugin data to the plugin_settings.json
        
        with open(plugin_settings) as data:
            plugin_data = json.load(data)

        return

class _PluginFileBindings():

    def __init__(self, inf, settings):

        self.uid = inf.get("uid")
        self.files = inf.get("files")
        self.methods = _PluginBindingMethods(inf.get("methods"), self)
        self.settings = settings

    def get_date_tree(self):

        data = {}
        data["uid"] = self.uid
        data["files"] = self.files
        data["methods"] = self.methods.get_date_tree()
        return data

class _PluginBindingMethods():

    def __init__(self, kwargs, file_binding):

        self.on_get = kwargs.get("on_get")
        self.on_save = kwargs.get("on_save")
        self.on_lock = kwargs.get("on_lock")
        self.on_icon_clicked = kwargs.get("on_icon_clicked")
        self.file_binding = file_binding

    def get_date_tree(self):

        data = {}
        data["on_get"] = self.on_get
        data["on_save"] = self.on_save
        data["on_lock"] = self.on_lock
        data["on_icon_clicked"] = self.on_icon_clicked
        return data

    def get(self, attr):

        return getattr(self, attr)

    def set(self, action, method):

        setattr(self, action, method)

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
            self.plugins.append(PluginSettingInfo(p, self))

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

    def save(self, plugin_name):
        """ Save the given plugin data to plugin_settings.json, override any exising settings.
        """

        plugin = [p for p in self.plugins if \
                  p.plugin_name == plugin_name]
        assert len(plugin) > 0, "Save Plugin error: plugin " + plugin_name + " not found."
        plugin = plugin[0]
        cur_plugin_data = plugin.get_data_tree()

        with open(plugin_settings) as data:
            plugin_data = json.load(data)

        new_data = []
        existing_plugins = plugin_data["plugins"]

        # add new plugin
        if not plugin_name in [p["plugin_name"] for p in existing_plugins]:
            Logger.Log.debug("Adding new plugin: " + plugin_name)
            plugin_data["plugins"].append(cur_plugin_data)

        # edit existing plugin
        else:
            Logger.Log.debug("Saving existing plugin: " + plugin_name)
            for i, p in enumerate(existing_plugins):
                if p["plugin_name"] == plugin_name:
                    new_data.append(cur_plugin_data)
                else:
                    new_data.append(p)

            plugin_data["plugins"] = new_data
        
        with open(plugin_settings, 'w') as data:
            json.dump(plugin_data, data, indent=4)

        # refresh plugins
        awsv_plugin_parser.get_plugin()