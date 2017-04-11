import ConfigParser
import os
import sys

class Config():

    cfgfile_path = os.path.dirname(__file__) + os.sep + "config.ini"

    def __init__(self, force=False):

        self.config = self.generate_config_file(force)
    
    def generate_config_file(self, force=False):

        _config = ConfigParser.ConfigParser()
        _config.optionxform = str

        if os.path.exists(cfgfile_path) and not force:
            _config.read(cfgfile_path)
            return _config

        _config.add_section("Main")
        _config.set('Main', 'AutoCheckFilesState', True)
        _config.set('Main', 'DefaultCommitMessage', "First Commit")

        _config.add_section("DisplayOptions")
        _config.set('DisplayOptions', 'ShowLockedFiles', True)
        _config.set('DisplayOptions', 'ShowLocalFiles', True)
        _config.set('DisplayOptions', 'ShowCloudFiles', True)
        _config.set('DisplayOptions', 'ShowUpToDateFiles', True)

        with open(self.cfgfile_path, 'w') as cfgfile:
            _config.write(cfgfile)

        return _config

    def get(self, section, option, _type):

        if _type == bool:
            return self.config.getboolean(section, option)
        elif _type == float:
            return self.config.getfloat(section, option)
        elif _type == int:
            return self.config.getint(section, option)
        else:
            return self.config.get(section, option)

    def set(self, section, option, value):
        
        self.config.set(section, option, value)

        with open(self.cfgfile_path, 'w') as cfgfile:
            self.config.write(cfgfile)