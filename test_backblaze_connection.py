#!/usr/bin/env python3
import argparse
import hashlib
import json
import logging
import os
import sys
import urllib.parse
from typing import Dict, Optional, Tuple

import requests


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s:%(name)s:%(message)s",
    )


def read_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Environment variable {name} is required")
    return value


def compute_sha1(file_path: str) -> str:
    hasher = hashlib.sha1()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def b2_authorize(key_id: str, app_key: str, proxies: Optional[Dict[str, str]] = None) -> Dict:
    logging.info("Authorizing with Backblaze B2...")
    resp = requests.get(
        "https://api.backblazeb2.com/b2api/v3/b2_authorize_account",
        auth=(key_id, app_key),
        timeout=30,
        proxies=proxies,
    )
    if resp.status_code != 200:
        raise SystemExit(f"Authorization failed: {resp.status_code} {resp.text}")
    return resp.json()


def b2_get_bucket(api_url: str, auth_token: str, account_id: str, bucket_name: str, proxies: Optional[Dict[str, str]] = None) -> Dict:
    logging.info("Resolving bucket id for '%s'...", bucket_name)
    resp = requests.post(
        f"{api_url}/b2api/v3/b2_get_bucket",
        headers={"Authorization": auth_token, "Content-Type": "application/json"},
        json={"accountId": account_id, "bucketName": bucket_name},
        timeout=30,
        proxies=proxies,
    )
    if resp.status_code != 200:
        raise SystemExit(f"Get bucket failed: {resp.status_code} {resp.text}")
    return resp.json()


def b2_get_upload_url(api_url: str, auth_token: str, bucket_id: str, proxies: Optional[Dict[str, str]] = None) -> Dict:
    logging.info("Requesting upload URL...")
    resp = requests.post(
        f"{api_url}/b2api/v3/b2_get_upload_url",
        headers={"Authorization": auth_token, "Content-Type": "application/json"},
        json={"bucketId": bucket_id},
        timeout=30,
        proxies=proxies,
    )
    if resp.status_code != 200:
        raise SystemExit(f"Get upload URL failed: {resp.status_code} {resp.text}")
    return resp.json()


def b2_upload_file(
    upload_url: str,
    upload_auth_token: str,
    local_file_path: str,
    destination_file_name: str,
    content_type: str = "b2/x-auto",
    proxies: Optional[Dict[str, str]] = None,
) -> Dict:
    logging.info("Uploading '%s' as '%s'...", local_file_path, destination_file_name)

    sha1_hex = compute_sha1(local_file_path)
    encoded_name = urllib.parse.quote(destination_file_name)

    with open(local_file_path, "rb") as fh:
        resp = requests.post(
            upload_url,
            headers={
                "Authorization": upload_auth_token,
                "X-Bz-File-Name": encoded_name,
                "Content-Type": content_type,
                "X-Bz-Content-Sha1": sha1_hex,
            },
            data=fh,
            timeout=120,
            proxies=proxies,
        )
    if resp.status_code != 200:
        raise SystemExit(f"Upload failed: {resp.status_code} {resp.text}")
    return resp.json()


def build_proxies(proxy_url: Optional[str]) -> Optional[Dict[str, str]]:
    if not proxy_url:
        return None
    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backblaze B2 minimal upload test using REST API.",
    )
    parser.add_argument("file", help="Path to local file to upload")
    parser.add_argument("dest", nargs="?", help="Destination file name in bucket (defaults to basename)")
    parser.add_argument("--proxy", dest="proxy", default=os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY"), help="Optional proxy URL (or set HTTP_PROXY/HTTPS_PROXY)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    local_file_path = args.file
    if not os.path.isfile(local_file_path):
        logging.error("File not found: %s", local_file_path)
        return 2

    destination_name = args.dest or os.path.basename(local_file_path)

    key_id = read_required_env("B2_KEY_ID")
    app_key = read_required_env("B2_APP_KEY")
    bucket_name = read_required_env("B2_BUCKET_NAME")

    proxies = build_proxies(args.proxy)

    auth = b2_authorize(key_id, app_key, proxies=proxies)
    api_url = auth.get("apiUrl")
    auth_token = auth.get("authorizationToken")
    account_id = auth.get("accountId")
    if not api_url or not auth_token or not account_id:
        logging.error("Authorization response missing fields: %s", json.dumps(auth))
        return 3
    logging.info("Authorized. Account: %s", account_id)

    bucket_resp = b2_get_bucket(api_url, auth_token, account_id, bucket_name, proxies=proxies)
    bucket_id = bucket_resp.get("bucketId")
    if not bucket_id:
        logging.error("Failed to resolve bucketId: %s", json.dumps(bucket_resp))
        return 4
    logging.info("Bucket id: %s", bucket_id)

    upload_resp = b2_get_upload_url(api_url, auth_token, bucket_id, proxies=proxies)
    upload_url = upload_resp.get("uploadUrl")
    upload_auth_token = upload_resp.get("authorizationToken")
    if not upload_url or not upload_auth_token:
        logging.error("Failed to get upload URL: %s", json.dumps(upload_resp))
        return 5

    final_resp = b2_upload_file(
        upload_url,
        upload_auth_token,
        local_file_path,
        destination_name,
        proxies=proxies,
    )

    file_id = final_resp.get("fileId")
    if not file_id:
        logging.error("Unexpected upload response: %s", json.dumps(final_resp))
        return 6

    logging.info("Upload succeeded. File ID: %s", file_id)
    print(file_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())