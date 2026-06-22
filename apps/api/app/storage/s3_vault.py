import os
from datetime import datetime, timezone
from typing import Optional, Tuple

_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is not None:
        return _s3_client
    endpoint = os.getenv("S3_ENDPOINT")
    if not endpoint:
        return None
    import boto3
    from botocore.client import Config

    _s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("S3_ACCESS_KEY", "minio"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY", "minio123"),
        config=Config(signature_version="s3v4"),
        region_name=os.getenv("S3_REGION", "us-east-1"),
    )
    return _s3_client


def s3_configured() -> bool:
    return bool(os.getenv("S3_ENDPOINT") and os.getenv("S3_BUCKET"))


def immutable_key(source: str, sha256: str, filename: str) -> str:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{source}/{date}/{sha256}/{filename}"


def store_s3(content: bytes, sha256: str, filename: str, source: str = "evidence") -> Tuple[str, bool]:
    client = _get_s3()
    bucket = os.getenv("S3_BUCKET", "enterprise-evidence")
    key = immutable_key(source, sha256, filename)
    if not client:
        raise RuntimeError("S3 not configured")
    try:
        client.head_object(Bucket=bucket, Key=key)
        return f"s3://{bucket}/{key}", False
    except Exception:
        client.put_object(Bucket=bucket, Key=key, Body=content, Metadata={"sha256": sha256})
        return f"s3://{bucket}/{key}", True
