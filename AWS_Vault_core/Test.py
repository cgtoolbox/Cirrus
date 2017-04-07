import time

from AWS_Vault_core import awsv_io
reload(awsv_io)

from AWS_Vault_core import awsv_connection
reload(awsv_connection)

def test_callback(b):
    print "callback => " + str(b)

def main():

    awsv_connection.CONNECTIONS["root"] = "D:/AWS/bfthecave/"
    test_file = "D:/AWS/bfthecave/filewith_metadata.txt"

    print("test file: " + test_file)

    client, resource = awsv_connection.init_connection()

    bucket = resource.Bucket("bfthecave")

    awsv_io.send_object(test_file, bucket, test_callback)

    #time.sleep(5)

    #r = awsv_io.checkout_file(True, test_file, bucket, "salut ca va ?")
    #print r

main()