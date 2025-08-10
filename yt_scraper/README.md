# yt-scraper (robust yt-dlp wrapper)

- Uses yt-dlp with curl-cffi and optional browser impersonation
- Supports cookies.txt for private/restricted videos
- Sensible defaults for formats, retries, and timeouts

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python yt_scrape.py URL [--cookies /path/to/cookies.txt] [--impersonate chrome]

# Download a playlist (preserves titles under playlist folder)
python yt_scrape.py PLAYLIST_URL --playlist
```

Options:
- --cookies: path to Netscape-format cookies.txt
- --impersonate: one of chrome, safari, edge, firefox (as supported by yt-dlp)
- --playlist: first enumerate entries, then download each with robust per-video opts
- --output: output template (default "%(title)s.%(ext)s")
- --dir: download directory (default ./downloads)