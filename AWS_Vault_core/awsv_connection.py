import os
import boto3
import datetime

from AWS_Vault_core import awsv_config

# skip dateutil unicode warning ( on windows only )
import warnings
warnings.filterwarnings("ignore", category=UnicodeWarning)

class _singleton(object):

    _states = {}

    def __init__(self):
        self.__dict__ = self._states

class ConnectionInfos(_singleton):

    def __init__(self, **kwargs):
        _singleton.__init__(self)
        self._states.update(kwargs)

    @classmethod
    def reset(cls):
        cls._states = {}

    @classmethod
    def get(cls, key):
        return cls._states[key]

    @classmethod
    def set(cls, key, value):
        cls._states[key] = value

    
CONNECTIONS = {"s3_client" : None,
               "s3_resource" : None,
               "root": None}

CURRENT_BUCKET = {"name" : None,
                  "bucket": None,
                  "local_root" : None,
                  "connection_time" : None}

def init_connection(bucket_name="", local_root="", reset=False):
    
    assert os.path.exists(local_root), "local root not valid: " + local_root
    local_root = local_root.replace('\\', '/')

    region_name = awsv_config.Config.get("BucketSettings", "DefaultRegionName", str)

    aws_session = boto3.session.Session(region_name=region_name)
    s3_client =  aws_session.client('s3', config= boto3.session.Config(signature_version='s3v4'))
    s3_resource = aws_session.resource('s3', config= boto3.session.Config(signature_version='s3v4'))

    try:
        s3_client.head_bucket(Bucket=bucket_name)
        bucket = s3_resource.Bucket(bucket_name)

    except botocore.exceptions.ClientError as e:
        print str(e)
        bucket = None

    if reset:
        ConnectionInfos.reset()

    ConnectionInfos(s3_client = s3_client)
    ConnectionInfos(region = region_name)
    ConnectionInfos(s3_resource = s3_resource)
    ConnectionInfos(s3_client = s3_client)
    ConnectionInfos(bucket = bucket)
    ConnectionInfos(bucket_name = bucket_name)
    ConnectionInfos(local_root = local_root + '/')
    ConnectionInfos(connection_time = datetime.datetime.now())

    return s3_client, s3_resource