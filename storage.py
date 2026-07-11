"""Wrapper fino sobre boto3/S3 para gravar objetos no MinIO do datalake."""

from __future__ import annotations

import json
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

BUCKET = os.getenv("MINIO_BUCKET", "rhid-datalake")

_client = boto3.client(
    "s3",
    endpoint_url=os.getenv("MINIO_ENDPOINT", "http://datalake-minio:9000"),
    aws_access_key_id=os.getenv("MINIO_USER"),
    aws_secret_access_key=os.getenv("MINIO_PASSWORD"),
    region_name="us-east-1",
)


def ensure_bucket(bucket: str = BUCKET) -> None:
    try:
        _client.head_bucket(Bucket=bucket)
    except ClientError:
        _client.create_bucket(Bucket=bucket)


def object_exists(key: str, bucket: str = BUCKET) -> bool:
    try:
        _client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


def put_json(key: str, obj: Any, bucket: str = BUCKET) -> None:
    body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    _client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")
