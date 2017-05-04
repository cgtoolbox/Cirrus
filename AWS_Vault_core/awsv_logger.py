import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from AWS_Vault_core import awsv_config

def init_logger():
    
    debug_level = awsv_config.Config.get("Log", "DebugLevel", str).upper()
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

    max_mb = awsv_config.Config.get("Log", "LogMaxSizeMb", int)
    backup_count = awsv_config.Config.get("Log", "LogBackupCount", int)
    log_filepath = awsv_config.Config.get("Log", "LogFilePath", str)
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
    
    return app_log

class Logger():

    Log = init_logger()

    @classmethod
    def delete_log(cls):
        log_filepath = awsv_config.Config.get("Log", "LogFilePath", str)
        if log_filepath == "default":
            logFile = os.environ["HOME"] + os.sep + 'awsv.log'
        else:
            logFile = log_filepath

        try:
            os.remove(logFile)
        except IOError:
            pass
            