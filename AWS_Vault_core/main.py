import os
import sys
import logging
import getpass
import socket
from logging.handlers import RotatingFileHandler
from PySide2 import QtGui

from AWS_Vault_core import awsv_widgets
reload(awsv_widgets)

def init_logger():

    log_formatter = logging.Formatter(('%(asctime)s [%(levelname)s]'
                                       '[%(module)s:%(funcName)s(%(lineno)d)] %(message)s'))
    logFile = os.environ["HOME"] + os.sep + 'awsv.log'

    handler = RotatingFileHandler(logFile, mode='a', maxBytes=100*1024*1024, 
                                     backupCount=2, encoding=None, delay=0)
    handler.setFormatter(log_formatter)
    handler.setLevel(logging.DEBUG)

    app_log = logging.getLogger('root')
    app_log.setLevel(logging.DEBUG)
    app_log.addHandler(handler)

def get_main_widget():
    
    init_logger()
    log = logging.getLogger("root")
    log.info("===================")
    log.info("=== New session ===")
    log.info("===================")
    log.info("user uid: " + getpass.getuser() + '@' + socket.gethostname())
    log.info("Executable: " + sys.executable)
    return awsv_widgets.MainWidget()

def launch_standalone(args):

    init_logger()
    app = QtGui.QGuiApplication(sys.argv)
    w = awsv_widgets.MainWidget()
    w.show()
    app.exec_()


if __name__ == "__main__":
    
    launch_standalone()