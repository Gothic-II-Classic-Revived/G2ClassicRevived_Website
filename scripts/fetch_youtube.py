from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from http_utils import fetch_text

API_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
DEFAULT_PLAYLIST_ID = "PL8S9wGaRCLIu8qv1tTgIxXHFLNkB1Qlhh"


def display_date(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%d.%m.%Y")
    except ValueError:
        return value[:10]


def fetch_playlist(api_key: str, playlist_id: str) -> list[dict[str, str]]:
    videos: list[dict[str, str]] = []
    page_token: str | None = None

    while True:
        params = {
            "part": "snippet",
            "maxResults": "50",
            "playlistId": playlist_id,
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        payload = json.loads(fetch_text(f"{API_URL}?{urlencode(params)}"))
        if "error" in payload:
            message = payload.get("error", {}).get("message", "Unknown YouTube API error")
            raise RuntimeError(message)

        for item in payload.get("items", []):
            snippet = item.get("snippet", {})
            resource = snippet.get("resourceId", {})
            video_id = resource.get("videoId")
            if not video_id:
                continue
            title = str(snippet.get("title", ""))
            if title in {"Deleted video", "Private video"}:
                continue
            published_at = str(snippet.get("publishedAt", ""))
            videos.append({
                "id": str(video_id),
                "title": title,
                "publishedAt": published_at,
                "date": display_date(published_at),
            })

        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    videos.sort(key=lambda video: video.get("publishedAt", ""), reverse=True)
    return videos


def write_manifest(site_dir: Path) -> list[dict[str, str]]:
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    playlist_id = os.getenv("YOUTUBE_PLAYLIST_ID", DEFAULT_PLAYLIST_ID).strip()
    allow_missing = os.getenv("ALLOW_MISSING_YOUTUBE_KEY", "0") == "1"

    if not api_key:
        if not allow_missing:
            raise RuntimeError(
                "YOUTUBE_API_KEY is not set. Add it as a GitHub Actions repository secret named YOUTUBE_API_KEY."
            )
        print("[youtube] WARNING: no API key; writing an empty videos manifest")
        videos: list[dict[str, str]] = []
    else:
        print(f"[youtube] Fetching playlist {playlist_id}")
        videos = fetch_playlist(api_key, playlist_id)
        print(f"[youtube] Found {len(videos)} videos")

    data_dir = site_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "videos.json").write_text(json.dumps(videos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return videos


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    write_manifest(target)
