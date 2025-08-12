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