import datetime
# skip dateutil unicode warning ( on windows only )
import warnings
warnings.filterwarnings("ignore", category=UnicodeWarning)

import boto3
import botocore

from CirrusCore.cirrus_logger import Logger
from CirrusCore import cirrus_config

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

def init_connection(bucket_name="", local_root="", reset=False):
    m = "Init connection, bucket_name={}, local_root={}".format(bucket_name,
                                                                local_root)
    Logger.Log.info(m)

    region_name = cirrus_config.Config.get("BucketSettings", "DefaultRegionName", str)

    aws_session = boto3.session.Session(region_name=region_name)
    s3_client = aws_session.client('s3', config=boto3.session.Config(signature_version='s3v4'))
    s3_resource = aws_session.resource('s3', config=boto3.session.Config(signature_version='s3v4'))

    dynamodb = aws_session.resource('dynamodb')
    database = dynamodb.Table(bucket_name)
    
    try:
        print database.creation_date_time

    except botocore.exceptions.ClientError:
        
        Logger.Log.info("Database {} not found, creating a new one.".format(bucket_name))
        database = dynamodb.create_table(TableName=bucket_name,
                                         KeySchema=[
                                                {
                                                    'AttributeName': 'uid',
                                                    'KeyType': 'HASH'
                                                }
                                             ],
                                            AttributeDefinitions=[
                                                {
                                                    'AttributeName': 'uid',
                                                    'AttributeType': boto3.dynamodb.types.STRING
                                                }
                                           ],
                                        ProvisionedThroughput={
                                            'ReadCapacityUnits': 10,
                                            'WriteCapacityUnits': 10
                                           }
                                       )
        database.meta.client.get_waiter('table_exists').wait(TableName=bucket_name)


    database.put_item(
        Item={
            'uid': 'coucoucocuocu',
            'desc' : 'test'
        }
    )

    print(database.item_count)

    if reset:
        ConnectionInfos.reset()
    
    ConnectionInfos(s3_client=s3_client)
    ConnectionInfos(region=region_name)
    ConnectionInfos(s3_resource=s3_resource)
    ConnectionInfos(database=database)
    
    if bucket_name != "" and local_root != "":

        try:
            s3_client.head_bucket(Bucket=bucket_name)
            bucket = s3_resource.Bucket(bucket_name)

        except botocore.exceptions.ClientError as err:
            Logger.Log.error(str(err))
            bucket = None

        local_root = local_root.replace('\\', '/')

        ConnectionInfos(bucket=bucket)
        ConnectionInfos(bucket_name=bucket_name)
        ConnectionInfos(local_root=local_root + '/')
        ConnectionInfos(connection_time=datetime.datetime.now())

    return s3_client, s3_resource
