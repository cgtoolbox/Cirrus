import os
import sys
import logging
import getpass
import socket
from logging.handlers import RotatingFileHandler
from PySide2 import QtGui

from CirrusCore import cirrus_widgets
reload(cirrus_widgets)
from CirrusCore import cirrus_config

from CirrusCore.cirrus_logger import Logger

def init_logger():

    debug_level = cirrus_config.Config.get("Log", "DebugLevel", str).upper()
    if debug_level == "INFO":
        debug_level = logging.INFO
    elif debug_level == "WARN":
        debug_level = logging.WARN
    elif debug_level == "ERROR":
        debug_level = logging.ERROR
    elif debug_level == "CRITICAL":
        debug_level = logging.CRITICAL
    else:
        debug_level = logging.DEBUG

    max_mb = cirrus_config.Config.get("Log", "LogMaxSizeMb", int)
    backup_count = cirrus_config.Config.get("Log", "LogBackupCount", int)
    log_filepath = cirrus_config.Config.get("Log", "LogFilePath", str)
    if log_filepath == "default":
        logFile = os.environ["HOME"] + os.sep + 'awsv.log'
    else:
        logFile = log_filepath
        assert os.path.exists(log_filepath), "CONFIG ERROR: invalid path: " + log_filepath

    log_formatter = logging.Formatter(('%(asctime)s [%(levelname)s]'
                                       '[%(module)s:%(funcName)s(%(lineno)d)] %(message)s'))
    

    handler = RotatingFileHandler(logFile, mode='a', maxBytes=max_mb*1024*1024, 
                                  backupCount=backup_count, encoding=None)
    handler.setFormatter(log_formatter)
    handler.setLevel(debug_level)

    app_log = logging.getLogger('root')
    app_log.setLevel(debug_level)
    app_log.addHandler(handler)

def get_main_widget():
    
    Logger.Log.info("=== New session ===")
    Logger.Log.info("user uid: " + getpass.getuser() + '@' + socket.gethostname())
    Logger.Log.info("Executable: " + sys.executable)
    return cirrus_widgets.MainWidget()

def launch_standalone(args):
    
    app = QtGui.QGuiApplication(sys.argv)
    w = cirrus_widgets.MainWidget()
    w.show()
    app.exec_()


if __name__ == "__main__":
    
    launch_standalone([])