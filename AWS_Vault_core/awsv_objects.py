import getpass
import datetime
import tempfile
import json
import uuid
import socket
import time
import os

from PySide2 import QtCore

from AWS_Vault_core import awsv_connection

METADATA_IDENTIFIER = ".awsvmd"

class FileState():

    NONE = -1
    LOCAL_ONLY = 0
    CLOUD_ONLY = 1
    CLOUD_AND_LOCAL_LATEST = 2
    CLOUD_AND_LOCAL_NOT_LATEST = 3

class ObjectState(object):

    __slot__ = ["local_path", "cloud_path", "locked", "message",
                "__root", "has_metadata"]

    def __init__(self, file_local_path):

        return

class ObjectMetadata(object):

    __slots__ = ["checked_out", "user", "time",
                 "message", "references", "extra_infos",
                 "__node_uuid", "__root", "__object_key"]

    def __init__(self, object_key=""):

        self.__root = awsv_connection.CURRENT_BUCKET["local_root"] + '/'
        self.__object_key = object_key.split('.')[0] + METADATA_IDENTIFIER
        
        self.checked_out = False
        self.user = ObjectMetadata.get_user_uid()
        self.time = str(datetime.datetime.now())
        self.message = ""
        self.references = []
        self.extra_infos = None

    @staticmethod
    def get_user_uid():
        return getpass.getuser() + '@' + socket.gethostname()

    def load(self, metadata):

        self.checked_out = metadata.get("checked_out", False)
        self.user = metadata.get("user", "")
        self.time = metadata.get("time", "")
        self.message = metadata.get("message", "")
        self.references = metadata.get("references", [])
        self.extra_infos = metadata.get("extra_infos")

    @property
    def data(self):

        _data = {}
        for k in self.__slots__:
            if k.startswith("__"): continue
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

    def dump(self):
         
        if self.__object_key == METADATA_IDENTIFIER:
            return False

        with open(self.__root + self.__object_key, 'w') as f:
            json.dump(self.data, f, indent=4)

        return self.__root + self.__object_key

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