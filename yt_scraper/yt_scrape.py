#!/usr/bin/env python3
import argparse
import os
import sys
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget


def build_common_opts(download_dir: str, output_template: str, cookies: str | None, impersonate: str | None) -> dict:
    opts: dict = {
        "quiet": False,
        "no_color": True,
        "paths": {"home": download_dir, "temp": os.path.join(download_dir, ".tmp")},
        "outtmpl": {
            "default": output_template,
            "chapter": "%(title)s - %(section_number)s %(section_title)s.%(ext)s",
        },
        # Prefer MP4/M4A; fall back gracefully
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        # Robustness
        "socket_timeout": 30,
        "ignore_no_formats_error": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragments": 5,
        "postprocessors": [
            {"key": "FFmpegMetadata"},
        ],
    }
    if cookies:
        opts["cookiefile"] = cookies
    if impersonate:
        opts["impersonate"] = ImpersonateTarget.from_str(impersonate)
    return opts


def download_single(url: str, opts: dict) -> int:
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.download([url])


def extract_playlist_entries(url: str, opts: dict):
    flat_opts = {**opts, "extract_flat": True, "noplaylist": False}
    with yt_dlp.YoutubeDL(flat_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        return []
    return info.get("entries", [])


def main():
    parser = argparse.ArgumentParser(description="Robust YouTube scraper using yt-dlp")
    parser.add_argument("url", help="Video or playlist URL")
    parser.add_argument("--cookies", help="Path to cookies.txt (Netscape format)")
    parser.add_argument("--impersonate", help="Impersonation target, e.g. chrome")
    parser.add_argument("--playlist", action="store_true", help="Treat URL as playlist and download entries")
    parser.add_argument("--dir", default="./downloads", help="Download directory")
    parser.add_argument("--output", default="%(title)s.%(ext)s", help="Output template")
    args = parser.parse_args()

    os.makedirs(args.dir, exist_ok=True)

    common_opts = build_common_opts(args.dir, args.output, args.cookies, args.impersonate)

    if not args.playlist:
        rc = download_single(args.url, common_opts)
        sys.exit(rc)

    entries = extract_playlist_entries(args.url, common_opts)
    if not entries:
        print("No entries found or failed to extract playlist", file=sys.stderr)
        sys.exit(1)

    # Per-video options: respect playlist folder in template by default
    per_opts = {
        **common_opts,
        "extract_flat": False,
        "outtmpl": {"default": "%(playlist_title)s/%(title)s.%(ext)s"},
    }

    errors = 0
    for idx, e in enumerate(entries, start=1):
        video_url = e.get("url") or e.get("webpage_url")
        if not video_url:
            continue
        print(f"[{idx}/{len(entries)}] Downloading {video_url}")
        rc = download_single(video_url, per_opts)
        if rc != 0:
            errors += 1

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()