import getpass
import datetime
import tempfile
import json
import uuid
import socket
import time
import os
import logging
from AWS_Vault_core.awsv_logger import Logger

from PySide2 import QtCore

from AWS_Vault_core.awsv_connection import ConnectionInfos
from awsv_config import Config

METADATA_IDENTIFIER = ".awsvmd"

class FileState():

    NONE = "None"
    LOCAL_ONLY = "Local Only"
    CLOUD_ONLY = "Cloud Only"
    CLOUD_AND_LOCAL_LATEST = "CLoud and local latest version"
    CLOUD_AND_LOCAL_NOT_LATEST = "Cloud and local not latest version"
    METADATA_DESYNC = "Metadata desync"

class FileLockState():

    UNLOCKED = 0
    LOCKED = 1
    SELF_LOCKED = 2

class ObjectState(object):

    __slot__ = ["local_path", "cloud_path", "locked", "message",
                "__root", "has_metadata"]

    def __init__(self, file_local_path):

        return

class ObjectMetadata(object):

    # version of the metadata object
    __version__ = 1.1

    # metadata attributes
    __slots__ = ["user", "creation_time", "latest_upload", "latest_upload_user", "is_latest",
                 "lock_message", "lock_time", "upload_message", "references", "extra_infos",
                 "version_id", "locals", "metadata_version",
                 "__root", "__object_key"]

    # attribute not saved on S3 server as it's only used locally
    __locals_only__ = ["is_latest", "version_id", "locals"]

    # attributes skipped by the "update" method
    __auto_generated__ = ["metadata_version"]

    def __init__(self, object_key=""):

        self.__root = ConnectionInfos.get("local_root")
        self.__object_key = object_key.split('.')[0] + METADATA_IDENTIFIER
        
        self.user = ""
        self.latest_upload_user = ""
        self.creation_time = datetime.datetime.now().ctime()
        self.lock_message = ""
        self.lock_time = ""
        self.upload_message = ""
        self.latest_upload = ""
        self.version_id = ""
        self.is_latest = False
        self.references = []
        self.extra_infos = None
        self.locals = ";".join(self.__locals_only__)
        self.metadata_version = self.__version__

    @staticmethod
    def get_user_uid():
        return getpass.getuser() + '@' + socket.gethostname()

    def load(self, metadata):
        """ Load given metadata dict to current object, set default values as well
        """
        self.user = metadata.get("user", "")
        self.latest_upload_user = metadata.get("latest_upload_user", "")
        self.latest_upload = metadata.get("latest_upload", "")
        self.upload_message = metadata.get("upload_message", "")
        self.references = metadata.get("references", [])
        self.extra_infos = metadata.get("extra_infos")
        self.lock_time = metadata.get("lock_time", "")
        self.version_id = metadata.get("version_id", "")
        self.is_latest = metadata.get("is_latest", False)
        self.locals = ";".join(self.__locals_only__)
        self.metadata_version = self.__version__

        lm = metadata.get("lock_message")
        if lm is not None and lm != "None":
            self.lock_message = lm

    def update(self, metadata):
        """ Update current metadata object with given dict values
        """
        for k, v in metadata.iteritems():

            if k in self.__auto_generated__:
                continue

            if hasattr(self, k):
                setattr(self, k, v)
    
    def data(self, remove_locals=True):

        _data = {}
        for k in self.__slots__:
            if k.startswith("__"): continue
            if remove_locals and k in self.__locals_only__: continue
            _data[k] = getattr(self, k)
        return _data

    @property
    def object_key(self):
        return self.__object_key

    def clean_tmp(self):

        p = self.__root + self.__object_key
        if os.path.exists(p):
            try:
                os.remove(p)
                return True
            except IOError:
                return False

    def dump(self, remove_locals=True):
         
        if self.__object_key == METADATA_IDENTIFIER:
            return False

        with open(self.__root + self.__object_key, 'w') as f:
            json.dump(self.data(remove_locals), f, indent=4)

        return self.__root + self.__object_key

    @classmethod
    def object_up_to_date(cls, metadata):

        v = metadata.get("metadata_version", None)
        if v is None:
            return False

        if v < cls.__version__:
            return False

        return True

    def get(self, k, default=None):

        if hasattr(self, k):
            return getattr(self, k)
        return default

class MetadataAccessResult(object):

    __slots__ = ["result", "message"]

    def __init__(self, result=False, message=""):
        
        self.result = result
        self.message = message

    def __str__(self):
        
        out = ("Access result ( metadata ):\n"
               "result: " + str(self.result) + "\n"
               "Message: " + str(self.message) + "\n")
        return out

    def __repr__(self):
        return self.__str__()
    
class BucketFolderElements(object):

    __slots__ = ["files", "metadata", "folders", "root", "files_size"]

    def __init__(self):

        self.root = ""
        self.files = []
        self.metadata = []
        self.folders = []
        self.files_size = []

    def __str__(self):

        out = "Root: " + str(self.root) + '\n'
        out += str(len(self.files)) + " File(s)\n"
        out += str(len(self.metadata)) + " Metadata file(s)\n"
        out += str(len(self.folders)) + " Folder(s)\n"
        return out

    def __repr__(self):
        return self.__str__()