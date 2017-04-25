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
        log.error(str(e))
        return None

def lock_object(object_path="", toggle=True, lock_message=""):
    """ Lock a given file according to "toggle" bool.
        An optional lock_message can be added to the metadata.
    """

    Bucket = ConnectionInfos.get("bucket")
    
    assert Bucket is not None, "Bucket is None"
    assert os.path.exists(object_path), "Object path not valid" + object_path

    local_root = ConnectionInfos.get("local_root")
    object_key = object_path.replace(local_root, '')

    log.debug("Lock file: " + object_path + " (" + str(toggle) + ')')

    now = datetime.datetime.now()

    if toggle:
        user_uid = awsv_objects.ObjectMetadata.get_user_uid()
        lock_time = now.ctime()
    else:
        user_uid = ""
        lock_time = ""
        lock_message = ""

    metadata = get_metadata(object_path)
    if not metadata:
        
        metadata = {"lock_message":lock_message,
                    "user":user_uid,
                    "latest_upload_user":"",
                    "lock_time":lock_time}
        generate_metadata(object_key=object_key, metadata=metadata)
    else:
        metadata["lock_message"] = lock_message
        metadata["user"] = user_uid
        metadata["lock_time"] = lock_time
        generate_metadata(object_key=object_key, metadata=metadata)

    return metadata

def get_metadata(object_path=""):
    """ Get the given object_path metadata on S3 vault, return None
        if not found.
    """
    
    Bucket = ConnectionInfos.get("bucket")
    
    assert Bucket is not None, "Bucket is None"
    
    object_path = object_path.replace('\\', '/')
    local_root = ConnectionInfos.get("local_root")
    object_key = object_path.replace(local_root, '')
    metadata_file = object_key.split('.', 1)[0] + awsv_objects.METADATA_IDENTIFIER
    metadata_path = os.path.dirname(object_path) + '/' + metadata_file.split('/')[-1]
    
    log.debug("Access metadata file: " + metadata_path)

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

def send_object(object_path="", message="", callback=None, keep_locked=False):
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
    if keep_locked:
        user = user_uid
        lock_message = "None"
    else:
        user = ""
        lock_message = ""

    now = datetime.datetime.now()
    metadata = {"upload_message":message,
                "latest_upload":now.ctime(),
                "lock_message":lock_message,
                "user":user,
                "latest_upload_user":user_uid}

    Bucket.upload_file(object_path, object_key,
                       ExtraArgs={"Metadata":metadata},
                       Callback=callback)

    generate_metadata(object_key, metadata=metadata)

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

def generate_metadata(object_key=None, metadata=None):
    """ Create a json metadata file locally and set it on s3 server.
    """
    Bucket = ConnectionInfos.get("bucket")
    assert Bucket is not None, "Bucket is None"

    m = awsv_objects.ObjectMetadata(object_key=object_key)
    if metadata:
        m.load(metadata)

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

    log.debug("Get local folder elements " + folder)

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

    log.debug("Get cloud folder element " + folder_name)

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