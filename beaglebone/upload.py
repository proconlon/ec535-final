"""
This script is run in a cron job on beagle bone
"""

import os
import glob
import boto3
from botocore.exceptions import BotoCoreError, ClientError

AWS_ACCESS_KEY_ID     = # fill in
AWS_SECRET_ACCESS_KEY = # fill in 
AWS_REGION            = os.getenv('AWS_REGION', 'us-east-1')
BUCKET_NAME           = # fill in

# Create S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)


def upload_and_cleanup(directory):
    """upload all csv files except for most recent one to the S3 bucket, in case most recent file is in use
    - deletes files that are uploaded"""
    pattern = os.path.join(directory, '*.csv')
    files = sorted(glob.glob(pattern), key=os.path.getmtime)
    if len(files) < 2:
        return 

    # skip the newest file (last in sorted list)
    to_upload = files[:-1]
    for filepath in to_upload:
        key = os.path.basename(filepath)
        try:
            print(f"Uploading {filepath} -> s3://{BUCKET_NAME}/{key}")
            s3.upload_file(filepath, BUCKET_NAME, key)
            print("  Success")
            os.remove(filepath)
        except (BotoCoreError, ClientError) as e:
            print(f"  Failed: {e}")

if __name__ == "__main__":
    for dir_name in ('logs', 'train'):
        if os.path.isdir(dir_name):
            upload_and_cleanup(dir_name)
        else:
            print(f"Directory not found: {dir_name}")
