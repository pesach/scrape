# scrape

## Backblaze B2 test script

Use the minimal script to authorize and upload a test file to a Backblaze B2 bucket via REST API.

Env vars required:
- `B2_KEY_ID`
- `B2_APP_KEY`
- `B2_BUCKET_NAME`

Example:
```bash
B2_KEY_ID=xxxx B2_APP_KEY=yyyy B2_BUCKET_NAME=my-bucket \
./scripts/test-backblaze.sh /path/to/local/file.txt optional-remote-name.txt
```

Run with `-h` for help.

---

## Python version of the Backblaze test

Install dependencies:
```bash
python3 -m pip install -r requirements.txt
```

Usage:
```bash
B2_KEY_ID=xxxx B2_APP_KEY=yyyy B2_BUCKET_NAME=my-bucket \
python3 scripts/test_backblaze_connection.py /path/to/local/file.txt optional-remote-name.txt
```

- Optional: pass a proxy with `--proxy http://user:pass@host:port` or via `HTTP_PROXY`/`HTTPS_PROXY` env vars.
- The script prints the uploaded file id on success and exits non-zero on failure.