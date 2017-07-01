import os
import datetime
import json
import tempfile
import shutil
from stat import S_IWRITE

from AWS_Vault_core.awsv_logger import Logger
from AWS_Vault_core import awsv_objects
reload(awsv_objects)
from AWS_Vault_core.awsv_connection import ConnectionInfos

import botocore

def get_object_key(object_path):
    """ Convert a local file path to a on cloud object key
    """
    object_path = object_path.replace('\\', '/')
    local_root = ConnectionInfos.get("local_root")
    object_key = object_path.replace(local_root, '')
    return object_key

def get_bucket(bucket_name=""):

    client = ConnectionInfos.get("s3_client")
    resource = ConnectionInfos.get("s3_resource")

    try:
        client.head_bucket(Bucket=bucket_name)
        return resource.Bucket(bucket_name)

    except botocore.exceptions.ClientError as e:
        Logger.Log.error(str(e))
        return None

def get_object_versions(object_path=""):
    """ Return all object versions enumerator.
    """
    Bucket = ConnectionInfos.get("bucket")

    Logger.Log.debug("[CLD_DOWN] Get object versions: " + object_path)
    object_key = get_object_key(object_path)

    try:
        return Bucket.object_versions.filter(Prefix=object_key)
    except botocore.exceptions.ClientError as e:
        Logger.Log.warning(str(e))
        return []

def lock_object(object_path="", toggle=True, lock_message=""):
    """ Lock a given file according to "toggle" bool.
        An optional lock_message can be added to the metadata.
    """

    Bucket = ConnectionInfos.get("bucket")
    
    assert Bucket is not None, "Bucket is None"
    assert os.path.exists(object_path), "Object path not valid" + object_path

    Logger.Log.debug("Lock file: " + object_path + " (" + str(toggle) + ')')

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
        
        _metadata = {"lock_message":lock_message,
                     "user":user_uid,
                     "latest_upload_user":"",
                     "lock_time":lock_time}
        generate_metadata(object_path=object_path, metadata=_metadata)
    else:
        _metadata = {"lock_message":lock_message,
                     "user":user_uid,
                     "lock_time":lock_time}
        metadata.update(_metadata)
        generate_metadata(object_path=object_path, metadata=metadata.data())

    return metadata

def get_metadata(object_path="", force_cloud=False, dump=True):
    """ Get the given object_path metadata on S3 vault, return None
        if not found.
        dump allows to save the cloud metadata to the local file.
    """
    
    Bucket = ConnectionInfos.get("bucket")
    assert Bucket is not None, "Bucket is None"

    # if the local file is not found then return None, 
    # as this means there might be a metadata / file desync
    if not os.path.exists(object_path):
        return None
    
    object_key = get_object_key(object_path)
    metadata_file = object_key.split('.', 1)[0] + awsv_objects.METADATA_IDENTIFIER
    metadata_path = os.path.dirname(object_path) + \
                    '/' + metadata_file.split('/')[-1]

    if not os.path.exists(metadata_path) and not force_cloud:
        Logger.Log.warning("Metadata missing: " + metadata_path)
        return None

    try:
        # if the local metadata doesn't exist, then download it from cloud
        # unless force_cloud is True
        if force_cloud:
            Logger.Log.debug("[CLD_DOWN] Access metadata file: " + metadata_path + \
                                " force_cloud: " + str(force_cloud))
            if not dump:
                metadata_path = tempfile.tempdir + os.sep + metadata_file.split('/')[-1] + ".tmp"
            
            obj = Bucket.Object(metadata_file)
            obj.download_file(metadata_path)

            with open(metadata_path) as f:
                data = json.load(f)

            if not dump:
                try:
                    os.remove(metadata_path)
                except IOError:
                    pass

        else:
            Logger.Log.debug("[LOCAL] Access metadata file: " + metadata_path + \
                             " force_cloud: " + str(force_cloud))
            with open(metadata_path) as f:
                data = json.load(f)

        metadata_version = data.get("metadata_version", -1.0)

        metadata = awsv_objects.ObjectMetadata(object_key)
        metadata.update(data)
        metadata.update({"metadata_version":metadata_version})  

        return metadata
        
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return None
        else:
            raise e

def generate_metadata(object_path=None, metadata=None, send_to_cloud=True):
    """ Create a json metadata file locally and set it on s3 server.
    """
    Bucket = ConnectionInfos.get("bucket")
    assert Bucket is not None, "Bucket is None"

    if not os.path.exists(object_path):
        return None

    object_key = get_object_key(object_path)

    m = awsv_objects.ObjectMetadata(object_key=object_key)
    if metadata:
        if not awsv_objects.ObjectMetadata.object_up_to_date(metadata):
            Logger.Log.warning("Metadata object outdated for file: " + str(object_path))
        m.update(metadata)

    Logger.Log.debug("[LOCAL] dump metadata (generated): " + object_path)
    
    if send_to_cloud:
        metadata_file = m.dump(remove_locals=True)
        Logger.Log.debug("[CLD_UP] send metadata (generated): " + object_path)
        Bucket.upload_file(metadata_file, Key=m.object_key)

    m.dump(remove_locals=False)

def send_object(object_path="", message="", callback=None, keep_locked=False):
    """ Send an object to ams S3 server, create new file if doesn't exist
        or update exsiting file. Arg callback is a funciton called to update
        transfert information ( in bytes )
    """
    Bucket = ConnectionInfos.get("bucket")

    assert os.path.exists(object_path), "object_path not valid"
    
    object_key = get_object_key(object_path)

    user_uid = awsv_objects.ObjectMetadata.get_user_uid()
    if keep_locked:
        # if kept locked, fetched the existing locked time and message
        cur_meta = get_metadata(object_path)
        user = user_uid
        lock_message = cur_meta.get("lock_message", "None")
        lock_time = cur_meta.get("lock_time", "")
    else:
        user = ""
        lock_message = ""
        lock_time = ""

    now = datetime.datetime.now()
    raw_metadata = {"upload_message":message,
                    "latest_upload":now.ctime(),
                    "lock_message":lock_message,
                    "lock_time":lock_time,
                    "user":user,
                    "latest_upload_user":user_uid}

    metadata = awsv_objects.ObjectMetadata(object_key)
    metadata.load(raw_metadata)

    Logger.Log.debug("[CLD_UP] send object: " + object_path)

    with open(object_path, "rb") as obj:

        s3_metadata = raw_metadata.copy()
        s3_metadata["latest_upload"] = now.ctime().replace(' ', '_').replace(':', '_')
        s3_metadata["lock_time"] = lock_time.replace(' ', '_').replace(':', '_')
        s3_metadata["lock_message"] = raw_metadata["lock_message"].decode("ascii", "ignore")
        s3_metadata["upload_message"] = raw_metadata["upload_message"].decode("ascii", "ignore")

        Bucket.upload_fileobj(obj, Key=object_key,
                              ExtraArgs={"Metadata":s3_metadata},
                              Callback=callback)
     
    metadata.update({"version_id":get_cloud_version_id(object_path)})
    metadata.update({"is_latest":True})

    generate_metadata(object_path, metadata=metadata.data(remove_locals=False))

def get_object_size(object_path=""):
    """ Get object size from S3 cloud
    """
    Bucket = ConnectionInfos.get("bucket")
    
    object_key = get_object_key(object_path)
    Logger.Log.debug("[CLD_DOWN] Get object size: " + object_path)

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
    
    object_key = get_object_key(object_path)

    Logger.Log.debug("[CLD_DOWN] Downloading file: " + object_path + " version_id: " + version_id)

    extra_args = None
    if version_id:
        extra_args = {"VersionId":version_id}

    # file is downloaded first to a temp file then copied to the right file
    temp_file = object_path + ".tmp"  
    Bucket.download_file(object_key, temp_file, ExtraArgs=extra_args, Callback=callback)

    if os.path.exists(object_path):
        os.chmod(object_path, S_IWRITE)
        shutil.copy2(temp_file, object_path)
    else:
        os.rename(temp_file, object_path)

    if os.path.exists(temp_file):
        os.remove(temp_file)

    metadata = get_metadata(object_path, force_cloud=True)

    # fetch latest version id
    if version_id == "":
        version_id = get_cloud_version_id(object_path)
        is_latest = True
    else:
        is_latest = False
    
    if not metadata:
        metadata = {"version_id":version_id}
        metadata["is_latest"] = is_latest
        generate_metadata(object_path, metadata=metadata)

    else:
        update_metadata = {"version_id":version_id,
                           "is_latest":is_latest}
        
        p, f = os.path.split(object_path)
        p = p.replace('\\', '/')
        f = f.split('.')[0] + awsv_objects.METADATA_IDENTIFIER

        _metadata = awsv_objects.ObjectMetadata(object_key)
        _metadata.update(update_metadata)
        _metadata.dump(False)

def get_local_version_id(object_path):
    """ Get the local file version_id saved in metadata
    """
    object_path = object_path.replace('\\', '/')
    metadata_file = object_path.split('.', 1)[0] + awsv_objects.METADATA_IDENTIFIER

    if not os.path.exists(metadata_file):
        return None

    with open(metadata_file) as f:
        data = json.load(f)

    ver = data.get("version_id", "")
    if ver == "":
        return None
    
    return ver
    
def get_cloud_version_id(object_path):
    """ Get the latest version_id from the cloud
    """
    client = ConnectionInfos.get("s3_client")
    bucket_name = ConnectionInfos.get("bucket_name")
    
    object_key = get_object_key(object_path)

    try:
        meta = client.head_object(Bucket=bucket_name, Key=object_key)
        cloud_ver = meta["VersionId"]
        return cloud_ver

    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return None
        raise e

def is_local_file_latest(object_path, local_ver=None, cloud_ver=None):
    """ Check if the local file version id matches the cloud one
        If the file doesn't exist on the cloud it will be tagged
        as up to date.
    """
    if not local_ver:
        local_ver = get_local_version_id(object_path)
    if not cloud_ver:
        cloud_ver = get_cloud_version_id(object_path)

    if local_ver is None and cloud_ver is None:
        return True

    if local_ver is None and not cloud_ver is None:
        return False

    if cloud_ver is None and not local_ver is None:
        return True

    return local_ver == cloud_ver

def remove_unused_metadata(metadata_file_path):
    """ If a metadata file is found but not its linked file, then remove
        the metadata file. Return True if the file has been removed.
    """
    root, f = os.path.split(metadata_file_path)
    f = f.split('.')[0]
    f_list = [n.split('.')[0] for n in os.listdir(root)\
              if n.split('.')[0] == f]
    if len(f_list) <= 1:
        Logger.Log.debug("[REM] Removing unused metadata: " + metadata_file_path)
        os.chmod(metadata_file_path, S_IWRITE)
        os.remove(metadata_file_path)
        return True
    return False

def get_local_folder_element(folder):

    if not os.path.exists(folder):
        Logger.Log.error("Folder {} doesn't exists".format(folder))
        return None

    Logger.Log.debug("Get local folder elements " + folder)

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
                if not remove_unused_metadata(element):
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

    Logger.Log.debug("Get cloud folder element " + folder_name)

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

def check_object(object_path="", version_id=None):
    """ Check if the object exists on the cloud
    """
    client = ConnectionInfos.get("s3_client")
    bucket_name = ConnectionInfos.get("bucket_name")
    
    object_key = get_object_key(object_path)
    
    try:
        if version_id is None:
            return client.head_object(Bucket=bucket_name, Key=object_key)
        else:
            return client.head_object(Bucket=bucket_name, Key=object_key, VersionId=version_id)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return None
        raise e

def refresh_state(object_path=""):
    """ Get the metadata from cloud and return file state, metadata
    """
    is_on_cloud = check_object(object_path)
    local_metatada = get_metadata(object_path, force_cloud=False)
    metadata = get_metadata(object_path, force_cloud=True, dump=False)

    # metadata desync, no metadata on cloud but file saved on cloud 
    # and metadata found locally
    if not metadata and local_metatada and is_on_cloud is not None:
        Logger.Log.warning("Metadata object cloud missing for file: " \
                            + str(object_path) + " regenerating it")
        metadata = generate_metadata(object_path, local_metatada.data(),
                                     True)

    # metadata outdated on cloud
    if metadata is not None and \
        not awsv_objects.ObjectMetadata.object_up_to_date(metadata):
        Logger.Log.warning("Metadata object outdated for file: " \
                            + str(object_path))
        if local_metatada:
            metadata = generate_metadata(object_path, local_metatada.data(),
                                         True)
        else:
            metadata = generate_metadata(object_path, None, True)

    local_version_id = None
    is_latest = ""
    if local_metatada:
        local_version_id = local_metatada.get("version_id", "")
        is_latest = local_metatada.get("is_latest", "")

    if metadata is not None:
        metadata.update({"version_id":local_version_id})
        metadata.update({"is_latest":is_latest})
    
    file_state = awsv_objects.FileState.NONE

    if os.path.exists(object_path):

        is_latest = is_local_file_latest(object_path, local_ver=local_version_id)
        if is_on_cloud and is_latest:
            file_state = awsv_objects.FileState.CLOUD_AND_LOCAL_LATEST

        elif is_on_cloud and not is_latest:
            if not local_metatada:
                file_state = awsv_objects.FileState.METADATA_DESYNC
            else:
                file_state = awsv_objects.FileState.CLOUD_AND_LOCAL_NOT_LATEST

        else:
            if not is_on_cloud:
                file_state = awsv_objects.FileState.LOCAL_ONLY

            if not local_metatada and is_on_cloud:
                file_state = awsv_objects.FileState.METADATA_DESYNC
    else:
        file_state = awsv_objects.FileState.CLOUD_ONLY

    if not metadata:
        return file_state, {}

    return file_state, metadata.data(remove_locals=False)