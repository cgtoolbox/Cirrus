import os
import getpass
import socket
import datetime
import json
import tempfile
import shutil
import datetime
import time
from stat import S_IREAD, S_IRGRP, S_IROTH, S_IWRITE
import logging
log = logging.getLogger("root")

from PySide2 import QtCore

from AWS_Vault_core import awsv_objects
reload(awsv_objects)

from AWS_Vault_core.awsv_connection import ConnectionInfos

import boto3
import botocore

def get_bucket(bucket_name=""):

    client = ConnectionInfos.get("s3_client")
    resource = ConnectionInfos.get("s3_resource")

    try:
        client.head_bucket(Bucket=bucket_name)
        return resource.Bucket(bucket_name)

    except botocore.exceptions.ClientError as e:
        print str(e)
        return None

def get_metadata(object_path=""):
    """ Get the given object_path metadata on S3 vault, return None
        if not found.
    """
    Bucket = ConnectionInfos.get("bucket")
    
    assert Bucket is not None, "Bucket is None"
    
    object_path = object_path.replace('\\', '/')
    local_root = ConnectionInfos.get("local_root")
    object_key = object_path.replace(local_root, '')
    metadata_file = object_key.split('.')[0] + awsv_objects.METADATA_IDENTIFIER

    metadata_path = os.path.dirname(object_path) + '/' + metadata_file

    try:
        obj = Bucket.Object(metadata_file)
        obj.download_file(metadata_path)

        with open(metadata_path) as f:
            data = json.load(f)
        return data
        
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return None
        else:
            raise e

def send_object(object_path="", message="", callback=None):
    """ Send an object to ams S3 server, create new file if doesn't exist
        or update exsiting file. Arg callback is a funciton called to update
        transfert information ( in bytes )
    """
    Bucket = ConnectionInfos.get("bucket")

    assert os.path.exists(object_path), "object_path not valid"
    
    object_path = object_path.replace('\\', '/')
    local_root = ConnectionInfos.get("local_root")
    object_key = object_path.replace(local_root, '')

    # lock the file before sending it to cloud
    os.chmod(object_path, S_IREAD|S_IRGRP|S_IROTH)

    user_uid = awsv_objects.ObjectMetadata.get_user_uid()
    now = datetime.datetime.now()

    metadata = {"message":message,
                "time":now.ctime(),
                "user":user_uid}

    Bucket.upload_file(object_path, object_key,
                       ExtraArgs={"Metadata":metadata},
                       Callback=callback)

    generate_metadata(object_key, message=message)

def get_object_size(object_path=""):
    """ Get object size from S3 cloud
    """
    Bucket = ConnectionInfos.get("bucket")

    object_path = object_path.replace('\\', '/')
    local_root = ConnectionInfos.get("local_root")
    object_key = object_path.replace(local_root, '')

    obj = Bucket.Object(object_key)
    try:
        return obj.content_length
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return 0
        else:
            raise e

def get_object(object_path="", version_id="", callback=None):
    """ Gets a given object onto the S3 cloud and download it locally
        Gets also the metadata file
    """
    Bucket = ConnectionInfos.get("bucket")

    object_path = object_path.replace('\\', '/')
    local_root = ConnectionInfos.get("local_root")
    object_key = object_path.replace(local_root, '')

    log.info("Downloading file: " + object_path + " version_id: " + version_id)

    # file is downloaded first to a temp file then copied to the right file
    temp_file = object_path + ".tmp"  
    Bucket.download_file(object_key, temp_file, Callback=callback)

    if os.path.exists(object_path):
        os.chmod(object_path, S_IWRITE)
        shutil.copy2(temp_file, object_path)
    else:
        os.rename(temp_file, object_path)

    if os.path.exists(temp_file):
        os.remove(temp_file)

    metadata = get_metadata(object_path)
    if not metadata:
        generate_metadata(object_key)
    else:
        p, f = os.path.split(object_path)
        p = p.replace('\\', '/')
        f = f.split('.')[0] + awsv_objects.METADATA_IDENTIFIER
        metadata_file = p + '/' + f
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=4)

def generate_metadata(object_key=None, checked_out=False,
                      message="Metadata creation"):
    """ Create a json metadata file locally and set it on s3 server.
    """
    Bucket = ConnectionInfos.get("bucket")
    assert Bucket is not None, "Bucket is None"

    m = awsv_objects.ObjectMetadata(object_key=object_key)
    m.checked_out = checked_out
    m.message = message
    metadata_file = m.dump()

    Bucket.upload_file(metadata_file, Key=m.object_key)

def checkout_file(toggle, object_path="", message=""):
    """ Checkout the given object on aws s3 server, that means it sets
        the metadata "checked_out" to True with a given ( optional ) message.
    """
    Bucket = ConnectionInfos.get("bucket")
    assert os.path.exists(object_path), "Object is None"
    assert Bucket is not None, "Bucket is None"
    
    result = awsv_objects.MetadataAccessResult()

    # check first metadata of the file
    meta = get_metadata(object_path, Bucket)
    if not meta:
        msg = "Object doesn't have metadata on server !"
        result.result = False
        result.message = msg
        return result

    # try to release the file, this can be achieved only by
    # the user who did checkout the file
    if toggle == False:
        user_id = getpass.getuser() + '@' + socket.gethostname()
        if meta["user"] != user_id:
            result.result = False
            result.message = "{} ({})".format(meta["message"], meta["user"])
            return result

    # try to checkout the file, only if the file is not
    # already checked out by another user.
    else:
        if meta["checked_out"]:
            result.result = False
            result.message = "{} ({})".format(meta["message"], meta["user"])
            return result

    object_path = object_path.replace('\\', '/')
    local_root = ConnectionInfos.get("local_root")
    object_key = object_path.replace(local_root, '')

    m = awsv_objects.ObjectMetadata(object_key=object_key)
    m.checked_out = toggle
    m.message = message
    m.time = str(datetime.datetime.now())
    metadata_file = m.dump()
    
    Bucket.upload_file(metadata_file, Key=m.object_key)

    result.message = ""
    result.result = True
    return result

def get_local_folder_element(folder):

    if not os.path.exists(folder):
        log.error("Folder {} doesn't exists".format(folder))
        return None

    log.info("Get local folder elements " + folder)

    elements = os.listdir(folder)
    local_root = ConnectionInfos.get("local_root")
    clean_root = folder.replace('\\', '/').replace(local_root, '')
    if clean_root == '/': clean_root = ''
    if clean_root.startswith('/'): clean_root = clean_root[1:]

    folders = []
    files = []
    meta_files = []
    f_sizes = []

    result = awsv_objects.BucketFolderElements()
    result.root = clean_root

    for element in elements:
        
        el = folder + '/' + element
        if not os.path.exists(el):
            continue

        if os.path.isdir(el):
            folders.append(clean_root + element)
        else:
            if element.endswith(awsv_objects.METADATA_IDENTIFIER):
                meta_files.append(element)
            else:
                s = os.path.getsize(el)
                f_sizes.append(s)
                files.append(clean_root + element)

    result.files = files
    result.folders = folders
    result.files_size = f_sizes
    result.metadata = meta_files

    return result

def get_bucket_folder_elements(folder_name=""):
    """ Get all folder elements ( aka: Sub Folders and Files + Metadata ) of a given
        Bucket + Folder name.
        Returns a awsv_objects.BucketFolderElements object.
    """
    Bucket = ConnectionInfos.get("bucket")

    log.info("Get cloud folder element " + folder_name)

    if folder_name != "":
        if not folder_name.endswith('/'): folder_name += '/'
    s3_client = ConnectionInfos.get("s3_client")

    result = awsv_objects.BucketFolderElements()
    result.root = folder_name

    raw = s3_client.list_objects_v2(Bucket=Bucket.name, Prefix=folder_name, Delimiter='/')
    folders = raw.get("CommonPrefixes")
    files = raw.get("Contents")

    if folders:
        result.folders = [f["Prefix"][0:-1] for f in folders]

    if files:

        f = []
        f_sizes = []
        meta_files = []
        for _file in files:
            
            fk = _file["Key"]

            if fk.endswith('/'): continue

            if fk.endswith(awsv_objects.METADATA_IDENTIFIER):
                meta_files.append(fk)
            else:
                f.append(fk)
                f_sizes.append(_file["Size"])

        result.files = f
        result.files_size = f_sizes
        result.metadata = meta_files

    return result

def check_object(object_path=""):

    client = ConnectionInfos.get("s3_client")
    bucket_name = ConnectionInfos.get("bucket_name")

    object_path = object_path.replace('\\', '/')
    local_root = ConnectionInfos.get("local_root")
    object_key = object_path.replace(local_root, '')

    try:
        client.head_object(Bucket=bucket_name, Key=object_key)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        raise e

class ElementFetcher(QtCore.QThread):

    end = QtCore.Signal(list)

    def __init__(self):
        super(ElementFetcher, self).__init__()
        self.data = None
        self.bucket = None
        self.folder_name = ""
        self.cancel = False

    def run(self):

        while self.bucket is None and self.folder_name == "":
            time.sleep(0.5)

        cloud_data = get_bucket_folder_elements(self.folder_name)

        if self.cancel: return
        
        local_root = ConnectionInfos.get("local_root")
        folder = local_root + self.folder_name

        local_data = get_local_folder_element(folder)
        if self.cancel: return

        self.end.emit([cloud_data, local_data])

class FileIOThread(QtCore.QThread):

    start_sgn = QtCore.Signal(int)
    update_progress_sgn = QtCore.Signal(int)
    end_sgn = QtCore.Signal(int)

    def __init__(self, local_file_path, mode=0, message=""):
        """ mode: 0 => upload, 1 => download
        """
        super(FileIOThread, self).__init__()
        self.local_file_path = local_file_path
        self.mode = mode
        self.message = message

    def update_progress(self, progress):
        
        self.update_progress_sgn.emit(progress)
    
    def run(self):
        
        self.start_sgn.emit(self.mode)
        if self.mode == 0:
            send_object(self.local_file_path, message=self.message,
                        callback=self.update_progress)
        else:
            get_object(self.local_file_path, callback=self.update_progress)
        self.end_sgn.emit(self.mode)

class FetchStateThread(QtCore.QThread):
    """ Used in PanelFileButtons when refresh state is needed
    """
    start_sgn = QtCore.Signal()
    end_sgn = QtCore.Signal(int)

    def __init__(self, local_file_path):
        super(FetchStateThread, self).__init__()
        self.local_file_path = local_file_path

    def run(self):

        self.start_sgn.emit()
        is_on_cloud = check_object(self.local_file_path)
        if is_on_cloud:

            if not os.path.exists(self.local_file_path):
                self.end_sgn.emit(awsv_objects.FileState.CLOUD_ONLY)
                return

            metadata = get_metadata(self.local_file_path)
            self.end_sgn.emit(awsv_objects.FileState.CLOUD_AND_LOCAL_LATEST)

        else:
            self.end_sgn.emit(awsv_objects.FileState.LOCAL_ONLY)

class DownloadProjectThread(QtCore.QThread):

    start_sgn = QtCore.Signal()
    start_element_download_sgn = QtCore.Signal(str, int)  # element name, element size ( bytes )
    update_download_progress_sgn = QtCore.Signal(int)  # bytes downloaded
    end_sgn = QtCore.Signal(int, int, str)  # statue, number of item downloaded, time spent

    def __init__(self, bucket, local_path):
        super(DownloadProjectThread, self).__init__()

        self.bucket = bucket
        self.local_path = local_path + '/'

    def update_progress(self, b):

        self.update_download_progress_sgn.emit(b)

    def run(self):

        start_time = datetime.datetime.now()

        self.start_sgn.emit()
        try:
            all_objects = self.bucket.objects.all()
        except Exception as e:
            self.end_sgn.emit(-1, 0, str(e))
            return

        n_elements = 0

        for obj in all_objects:
            
            key = obj.key

            # create folder
            if key.endswith('/'):
                key = key[0:-1]
                os.makedirs(self.local_path + key)
                continue
            
            # download object
            path = self.local_path + key
            _object = obj.Object()
            
            self.start_element_download_sgn.emit(key, obj.size)

            try:
                _object.download_file(path, Callback=self.update_progress)
            except Exception as e:
                self.end_sgn.emit(-1, 0, str(e))
                return

            n_elements += 1

        end_time = datetime.datetime.now()

        time_elapsed = str(end_time - start_time)

        self.end_sgn.emit(1, 0, time_elapsed)
