import os
import getpass
import socket
import datetime
import json
import tempfile
import shutil
from stat import S_IREAD, S_IRGRP, S_IROTH, S_IWRITE

from PySide2 import QtCore

from AWS_Vault_core import awsv_connection
reload(awsv_connection)
from AWS_Vault_core import awsv_objects
reload(awsv_objects)

import boto3
import botocore

def get_bucket(bucket_name=""):

    client = awsv_connection.CONNECTIONS["s3_client"]
    resource = awsv_connection.CONNECTIONS["s3_resource"]

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
    Bucket = awsv_connection.CURRENT_BUCKET["bucket"]

    assert os.path.exists(object_path), "object_path not valid"
    assert Bucket is not None, "Bucket is None"

    tmp = tempfile.gettempdir().replace('\\', '/') + '/'

    object_path = object_path.replace('\\', '/')
    root = awsv_connection.CONNECTIONS["root"]
    object_key = object_path.replace(root, '')
    metadata_file = object_key.split('.')[0] + "_meta.json"

    try:
        obj = Bucket.Object(metadata_file)
        obj.download_file(tmp + metadata_file)

        with open(tmp + metadata_file) as f:
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
    Bucket = awsv_connection.CURRENT_BUCKET["bucket"]

    assert os.path.exists(object_path), "object_path not valid"
    
    object_path = object_path.replace('\\', '/')
    root = awsv_connection.CONNECTIONS["root"]
    object_key = object_path.replace(root, '')

    # lock the file before sending it to cloud
    os.chmod(object_path, S_IREAD|S_IRGRP|S_IROTH)

    Bucket.upload_file(object_path, object_key, Callback=callback)

    generate_metadata(object_key, message=message)

def get_object_size(object_path=""):
    """ Get object size from S3 cloud
    """
    Bucket = awsv_connection.CURRENT_BUCKET["bucket"]

    assert os.path.exists(object_path), "object_path not valid"

    object_path = object_path.replace('\\', '/')
    root = awsv_connection.CONNECTIONS["root"]
    object_key = object_path.replace(root, '')

    obj = Bucket.Object(object_key)
    try:
        return obj.content_length
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return None
        else:
            raise e

def get_object(object_path="", version_id="", callback=None):
    """ Gets a given object onto the S3 cloud and download it locally
        Gets also the metadata file
    """
    Bucket = awsv_connection.CURRENT_BUCKET["bucket"]

    assert os.path.exists(object_path), "object_path not valid"

    object_path = object_path.replace('\\', '/')
    root = awsv_connection.CONNECTIONS["root"]
    object_key = object_path.replace(root, '')

    # file is downloaded first to a temp file then copied to the right file
    temp_file = object_path + ".tmp"  
    Bucket.download_file(object_key, temp_file, Callback=callback)

    os.chmod(object_path, S_IWRITE)
    shutil.copy2(temp_file, object_path)

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

def generate_metadata(object_key=None, message="Metadata creation"):
    """ Create a json metadata file locally and set it on s3 server.
    """
    Bucket = awsv_connection.CURRENT_BUCKET["bucket"]
    assert Bucket is not None, "Bucket is None"

    m = awsv_objects.ObjectMetadata(object_key=object_key)
    m.checked_out = False
    m.message = message
    metadata_file = m.dump()

    Bucket.upload_file(metadata_file, Key=m.object_key)

def checkout_file(toggle, object_path="", message=""):
    """ Checkout the given object on aws s3 server, that means it sets
        the metadata "checked_out" to True with a given ( optional ) message.
    """
    Bucket = awsv_connection.CURRENT_BUCKET["bucket"]
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
    root = awsv_connection.CONNECTIONS["root"]
    object_key = object_path.replace(root, '')

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
        return None

    elements = os.listdir(folder)
    local_root = awsv_connection.CURRENT_BUCKET["local_root"].replace('\\', '/')
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
    Bucket = awsv_connection.CURRENT_BUCKET["bucket"]

    if folder_name != "":
        if not folder_name.endswith('/'): folder_name += '/'
    s3_client = awsv_connection.CONNECTIONS["s3_client"]

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
        
        root = awsv_connection.CURRENT_BUCKET["local_root"].replace('\\', '/')
        folder = root + '/' + self.folder_name

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