import ConfigParser
import os
import sys
import logging
log = logging.getLogger("root")

"""
    Configuration options singleton.
"""

def generate_config_file():
        
    cfgfile_path = os.path.dirname(__file__) + os.sep + "config.ini"
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    
    if os.path.exists(cfgfile_path):
        config.read(cfgfile_path)
        return config

    log.info("Config file not found, creating a new one.")

    config.add_section("Main")
    config.set('Main', 'AutoCheckFilesState', True)
    config.set('Main', 'DefaultCommitMessage', "First Commit")

    config.add_section("BucketSettings")
    config.set("BucketSettings", "DefaultRegionName", "eu-central-1")
    
    config.add_section("DisplayOptions")
    config.set('DisplayOptions', 'ShowLockedFiles', True)
    config.set('DisplayOptions', 'ShowLocalFiles', True)
    config.set('DisplayOptions', 'ShowCloudFiles', True)
    config.set('DisplayOptions', 'ShowUpToDateFiles', True)

    with open(cfgfile_path, 'w') as cfgfile:
        config.write(cfgfile)

    return config

class Config():
    
    config = generate_config_file()

    @classmethod
    def get(cls, section, option, _type):

        if _type == bool:
            return cls.config.getboolean(section, option)
        elif _type == float:
            return cls.config.getfloat(section, option)
        elif _type == int:
            return cls.config.getint(section, option)
        else:
            return cls.config.get(section, option)
    
    @classmethod
    def set(cls, section, option, value):
        
        cls.config.set(section, option, value)

        with open(cls.cfgfile_path, 'w') as cfgfile:
            cls.config.write(cfgfile)