#!/usr/bin/env bash
set -euo pipefail
BUCKET="${S3_BUCKET:-enterprise-evidence}"
ENDPOINT="${S3_ENDPOINT:-http://127.0.0.1:9000}"
ACCESS="${S3_ACCESS_KEY:-minio}"
SECRET="${S3_SECRET_KEY:-minio123}"

python3 - <<PY
import boto3
from botocore.client import Config
client = boto3.client('s3', endpoint_url='$ENDPOINT', aws_access_key_id='$ACCESS', aws_secret_access_key='$SECRET', config=Config(signature_version='s3v4'), region_name='us-east-1')
try:
    client.head_bucket(Bucket='$BUCKET')
    print('bucket exists')
except Exception:
    client.create_bucket(Bucket='$BUCKET')
    print('bucket created')
PY
