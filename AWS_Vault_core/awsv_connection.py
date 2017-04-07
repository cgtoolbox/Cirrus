import boto3

# skip dateutil unicode warning ( on windows only )
import warnings
warnings.filterwarnings("ignore", category=UnicodeWarning)

CONNECTIONS = {"s3_client" : None,
               "s3_resource" : None,
               "root": None}

CURRENT_BUCKET = {"name" : None,
                  "bucket": None,
                  "local_root" : None,
                  "connection_time" : None}

def init_connection(region_name="eu-central-1"):
    
    aws_session = boto3.session.Session(region_name=region_name)
    s3_client =  aws_session.client('s3', config= boto3.session.Config(signature_version='s3v4'))
    s3_resource = aws_session.resource('s3', config= boto3.session.Config(signature_version='s3v4'))

    CONNECTIONS["s3_client"] = s3_client
    CONNECTIONS["s3_resource"] = s3_resource

    return s3_client, s3_resource