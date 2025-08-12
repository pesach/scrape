#!/usr/bin/env bash
set -euo pipefail

# Minimal Backblaze B2 upload test using raw REST API.
# Requirements: bash, curl, and either `sha1sum` or `openssl`.
# JSON parsing is done with python3 if available, else `jq` if present.

# Usage:
#   B2_KEY_ID=xxx B2_APP_KEY=yyy B2_BUCKET_NAME=my-bucket \
#   ./scripts/test-backblaze.sh /path/to/local/file [dest-file-name]

if [[ ${1-} == "-h" || ${1-} == "--help" || $# -lt 1 ]]; then
  echo "Usage: B2_KEY_ID=... B2_APP_KEY=... B2_BUCKET_NAME=... $0 /path/to/file [dest-file-name]"
  exit 1
fi

: "${B2_KEY_ID:?B2_KEY_ID is required}"
: "${B2_APP_KEY:?B2_APP_KEY is required}"
: "${B2_BUCKET_NAME:?B2_BUCKET_NAME is required}"

LOCAL_FILE_PATH="$1"
if [[ ! -f "$LOCAL_FILE_PATH" ]]; then
  echo "File not found: $LOCAL_FILE_PATH" >&2
  exit 1
fi
DEST_FILE_NAME="${2-}"
if [[ -z "$DEST_FILE_NAME" ]]; then
  DEST_FILE_NAME="$(basename "$LOCAL_FILE_PATH")"
fi

has_cmd() { command -v "$1" >/dev/null 2>&1; }

parse_json() {
  # parse_json <json> <jq-like-key>
  # prefers python3; falls back to jq
  local json="$1"; shift
  local key="$1"; shift
  if has_cmd python3; then
    python3 - "$key" <<'PY' <<<"$json"
import sys, json
key = sys.argv[1]
obj = json.load(sys.stdin)
# support dotted keys, e.g. allowed.bucketId
cur = obj
for part in key.split('.'):
    if isinstance(cur, list):
        try:
            idx = int(part)
            cur = cur[idx]
        except:
            cur = None
            break
    else:
        cur = cur.get(part)
        if cur is None:
            break
print('' if cur is None else cur)
PY
  elif has_cmd jq; then
    echo "$json" | jq -r ".${key} // \"\""
  else
    echo "Error: Neither python3 nor jq is available for JSON parsing." >&2
    exit 1
  fi
}

compute_sha1() {
  local file="$1"
  if has_cmd sha1sum; then
    sha1sum "$file" | awk '{print $1}'
  elif has_cmd openssl; then
    # openssl sha1 prints: SHA1(file)= <hash> or with -r: <hash> <file>
    openssl sha1 -r "$file" | awk '{print $1}'
  else
    echo "Error: Need sha1sum or openssl to compute SHA1." >&2
    exit 1
  fi
}

info() { echo "[info] $*"; }

# 1) Authorize
info "Authorizing with Backblaze B2..."
AUTH_JSON=$(curl -sS -u "${B2_KEY_ID}:${B2_APP_KEY}" "https://api.backblazeb2.com/b2api/v3/b2_authorize_account")
API_URL=$(parse_json "$AUTH_JSON" apiUrl)
AUTH_TOKEN=$(parse_json "$AUTH_JSON" authorizationToken)
ACCOUNT_ID=$(parse_json "$AUTH_JSON" accountId)
if [[ -z "$API_URL" || -z "$AUTH_TOKEN" || -z "$ACCOUNT_ID" ]]; then
  echo "Failed to authorize. Response was:" >&2
  echo "$AUTH_JSON" >&2
  exit 1
fi
info "Authorized. Account: $ACCOUNT_ID"

# 2) Resolve bucketId by name
info "Resolving bucket id for '$B2_BUCKET_NAME'..."
GET_BUCKET_JSON=$(curl -sS -H "Authorization: ${AUTH_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d "{\"accountId\":\"${ACCOUNT_ID}\",\"bucketName\":\"${B2_BUCKET_NAME}\"}" \
  "$API_URL/b2api/v3/b2_get_bucket")
BUCKET_ID=$(parse_json "$GET_BUCKET_JSON" bucketId)
if [[ -z "$BUCKET_ID" ]]; then
  echo "Failed to get bucket. Response was:" >&2
  echo "$GET_BUCKET_JSON" >&2
  exit 1
fi
info "Bucket id: $BUCKET_ID"

# 3) Get upload URL
info "Requesting upload URL..."
UPLOAD_URL_JSON=$(curl -sS -H "Authorization: ${AUTH_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d "{\"bucketId\":\"${BUCKET_ID}\"}" \
  "$API_URL/b2api/v3/b2_get_upload_url")
UPLOAD_URL=$(parse_json "$UPLOAD_URL_JSON" uploadUrl)
UPLOAD_AUTH_TOKEN=$(parse_json "$UPLOAD_URL_JSON" authorizationToken)
if [[ -z "$UPLOAD_URL" || -z "$UPLOAD_AUTH_TOKEN" ]]; then
  echo "Failed to get upload URL. Response was:" >&2
  echo "$UPLOAD_URL_JSON" >&2
  exit 1
fi
info "Obtained upload URL."

# 4) Compute SHA1 and upload
FILE_SHA1=$(compute_sha1 "$LOCAL_FILE_PATH")
CONTENT_TYPE="b2/x-auto"

info "Uploading '$LOCAL_FILE_PATH' as '$DEST_FILE_NAME'..."
UPLOAD_RESP=$(curl -sS -X POST \
  -H "Authorization: ${UPLOAD_AUTH_TOKEN}" \
  -H "X-Bz-File-Name: $(python3 - <<PY 2>/dev/null; [[ $? -eq 0 ]] || echo "$DEST_FILE_NAME" | sed 's/ /%20/g'
import urllib.parse, sys
print(urllib.parse.quote(sys.argv[1]))
PY "$DEST_FILE_NAME")" \
  -H "Content-Type: ${CONTENT_TYPE}" \
  -H "X-Bz-Content-Sha1: ${FILE_SHA1}" \
  --data-binary @"${LOCAL_FILE_PATH}" \
  "$UPLOAD_URL")

FILE_ID=$(parse_json "$UPLOAD_RESP" fileId)
if [[ -z "$FILE_ID" ]]; then
  echo "Upload failed. Response was:" >&2
  echo "$UPLOAD_RESP" >&2
  exit 1
fi

info "Upload succeeded. File ID: $FILE_ID"