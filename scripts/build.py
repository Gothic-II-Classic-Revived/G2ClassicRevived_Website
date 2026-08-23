from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from fetch_youtube import write_manifest  # noqa: E402
from sync_images import sync_images  # noqa: E402


def tree_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def human_size(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB"]
    number = float(value)
    for unit in units:
        if number < 1024 or unit == units[-1]:
            return f"{number:.2f} {unit}"
        number /= 1024
    return f"{value} B"


def main() -> None:
    source = PROJECT_DIR / "site"
    output = PROJECT_DIR / "_site"

    print(f"[build] Creating clean build directory: {output}")
    shutil.rmtree(output, ignore_errors=True)
    shutil.copytree(source, output)

    images = sync_images(output)
    videos = write_manifest(output)

    # Build metadata intentionally contains no source URLs or secrets.
    info = {
        "builtAt": datetime.now(timezone.utc).isoformat(),
        "images": len(images),
        "videos": len(videos),
        "youtubePlaylistId": os.getenv("YOUTUBE_PLAYLIST_ID", "PL8S9wGaRCLIu8qv1tTgIxXHFLNkB1Qlhh"),
    }
    (output / "data" / "build.json").write_text(
        json.dumps(info, indent=2) + "\n",
        encoding="utf-8",
    )

    (output / ".nojekyll").write_text("", encoding="utf-8")

    size = tree_size(output)
    print(f"[build] Finished: {len(images)} images, {len(videos)} videos, {human_size(size)}")

    supported_limit = 1024 * 1024 * 1024
    if size > supported_limit and os.getenv("ALLOW_OVERSIZE_PAGES_ARTIFACT", "0") != "1":
        raise RuntimeError(
            f"Built site is {human_size(size)}, over the 1 GiB supported GitHub Pages site size. "
            "Reduce generated media size before deploying."
        )


if __name__ == "__main__":
    main()
