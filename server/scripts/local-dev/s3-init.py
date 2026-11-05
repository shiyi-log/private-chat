#!/usr/bin/env python3
"""Initialize and verify the isolated local S3 store without an external CLI."""

import datetime
import hashlib
import hmac
import os
import time
import urllib.error
import urllib.request


def request(method, path, payload=b""):
    endpoint = "http://minio:9000"
    host = "minio:9000"
    access_key = os.environ["MINIO_ROOT_USER"]
    secret_key = os.environ["MINIO_ROOT_PASSWORD"]
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.strftime("%Y%m%dT%H%M%SZ")
    date = now.strftime("%Y%m%d")
    digest = hashlib.sha256(payload).hexdigest()
    canonical_headers = f"host:{host}\nx-amz-content-sha256:{digest}\nx-amz-date:{timestamp}\n"
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join((method, path, "", canonical_headers, signed_headers, digest))
    scope = f"{date}/us-east-1/s3/aws4_request"
    string_to_sign = "\n".join(("AWS4-HMAC-SHA256", timestamp, scope, hashlib.sha256(canonical_request.encode()).hexdigest()))
    key = ("AWS4" + secret_key).encode()
    for part in (date, "us-east-1", "s3", "aws4_request"):
        key = hmac.new(key, part.encode(), hashlib.sha256).digest()
    signature = hmac.new(key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    headers = {
        "Host": host,
        "x-amz-date": timestamp,
        "x-amz-content-sha256": digest,
        "Authorization": f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, SignedHeaders={signed_headers}, Signature={signature}",
    }
    req = urllib.request.Request(endpoint + path, data=payload if method == "PUT" else None, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read()


for attempt in range(60):
    try:
        request("GET", "/")
        break
    except (OSError, urllib.error.HTTPError):
        if attempt == 59:
            raise
        time.sleep(1)

for bucket in ("documents", "encryptedfiles", "photos", "videos"):
    try:
        request("PUT", "/" + bucket)
    except urllib.error.HTTPError as error:
        if error.code != 409:
            raise
        request("HEAD", "/" + bucket)
    path = f"/{bucket}/privatechat-local-integration-probe"
    payload = f"private-chat:{bucket}:roundtrip".encode()
    request("PUT", path, payload)
    if request("GET", path) != payload:
        raise RuntimeError(f"S3 roundtrip mismatch: {bucket}")
    request("DELETE", path)
    print(f"S3 bucket verified: {bucket}", flush=True)
