from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlparse

from PIL import Image, ImageOps

from http_utils import fetch_bytes, fetch_text

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
DATE_FORMAT = "%d-%m-%Y_%H-%M"
DUPLICATE_SUFFIX_RE = re.compile(r" \(\d+\)$")


@dataclass(frozen=True)
class RemoteImage:
    filename: str
    url: str
    parsed_date: datetime
    raw_name: str


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.hrefs.append(value)
                break


def parse_image_date(filename: str) -> tuple[datetime, str] | None:
    raw_name = Path(filename).stem
    base_name = DUPLICATE_SUFFIX_RE.sub("", raw_name)
    try:
        return datetime.strptime(base_name, DATE_FORMAT), raw_name
    except ValueError:
        return None


def normalize_candidate(url: str) -> RemoteImage | None:
    parsed = urlparse(url)
    filename = unquote(Path(parsed.path).name)
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        return None

    parsed_date = parse_image_date(filename)
    if not parsed_date:
        return None

    date, raw_name = parsed_date
    parent = url.rsplit("/", 1)[0] + "/"
    safe_url = urljoin(parent, quote(filename, safe="()[]-_.'"))
    return RemoteImage(filename=filename, url=safe_url, parsed_date=date, raw_name=raw_name)


def images_from_entries(entries: list[object], base_url: str) -> list[RemoteImage]:
    found: dict[str, RemoteImage] = {}

    for entry in entries:
        if isinstance(entry, str):
            candidate = entry
        elif isinstance(entry, dict):
            candidate = str(entry.get("url") or entry.get("path") or entry.get("filename") or "")
        else:
            continue

        candidate = candidate.strip()
        if not candidate:
            continue

        item = normalize_candidate(urljoin(base_url, candidate))
        if item:
            found[item.filename] = item

    return list(found.values())


def discover_from_json(text: str, source_url: str) -> list[RemoteImage]:
    data = json.loads(text)

    base_url = source_url
    if isinstance(data, dict):
        configured_base = data.get("base_url") or data.get("baseUrl")
        if configured_base:
            base_url = urljoin(source_url, str(configured_base))
        data = data.get("images", [])

    if not isinstance(data, list):
        raise ValueError("Image manifest must be a JSON array or an object with an 'images' array")

    return images_from_entries(data, base_url)


def discover_from_directory_listing(text: str, source_url: str) -> list[RemoteImage]:
    parser = LinkCollector()
    parser.feed(text)
    return images_from_entries(parser.hrefs, source_url)


def discover_from_plaintext(text: str, source_url: str) -> list[RemoteImage]:
    entries: list[object] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(line)
    return images_from_entries(entries, source_url)


def discover_from_source(source_url: str) -> list[RemoteImage]:
    text = fetch_text(source_url).lstrip("\ufeff\r\n\t ")
    if not text:
        raise ValueError("Configured image source returned an empty response")

    json_error: json.JSONDecodeError | None = None
    try:
        return discover_from_json(text, source_url)
    except json.JSONDecodeError as exc:
        json_error = exc

    # A secret may point directly at an Apache/nginx auto-index instead of a
    # JSON file. Keep using the same variable and discover image hrefs there.
    html_images = discover_from_directory_listing(text, source_url)
    if html_images:
        return html_images

    # Also allow a minimal newline-separated manifest without requiring JSON.
    text_images = discover_from_plaintext(text, source_url)
    if text_images:
        return text_images

    raise ValueError(
        "Configured image source was neither a usable JSON manifest, directory listing, "
        f"nor newline-separated file list (JSON parse error: {json_error})"
    )


def discover_images() -> list[RemoteImage]:
    source_url = os.getenv("VPS_IMAGE_MANIFEST_URL", "").strip()
    if not source_url:
        if os.getenv("ALLOW_EMPTY_IMAGES", "0") == "1":
            print("[images] WARNING: VPS_IMAGE_MANIFEST_URL is not set; ALLOW_EMPTY_IMAGES=1 so build will continue")
            return []
        raise RuntimeError("Missing required environment variable: VPS_IMAGE_MANIFEST_URL")

    # Never print the configured URL because it may be stored as an Actions secret.
    print("[images] Discovering images from configured source")
    try:
        images = discover_from_source(source_url)
    except Exception as exc:
        if os.getenv("ALLOW_EMPTY_IMAGES", "0") == "1":
            print(f"[images] WARNING: image discovery failed: {exc}")
            return []
        raise RuntimeError(f"Unable to read configured image source: {exc}") from exc

    if not images:
        if os.getenv("ALLOW_EMPTY_IMAGES", "0") == "1":
            print("[images] WARNING: source contained no dated images; ALLOW_EMPTY_IMAGES=1 so build will continue")
            return []
        raise RuntimeError("Configured image source contained no files matching the expected dated image filenames")

    images.sort(key=lambda item: (item.parsed_date, item.filename), reverse=True)
    print(f"[images] Found {len(images)} dated images")
    return images


def prepare_image(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    if getattr(image, "is_animated", False):
        image.seek(0)
    image.load()
    if image.mode not in ("RGB", "L"):
        background = Image.new("RGB", image.size, "black")
        if "A" in image.getbands():
            background.paste(image, mask=image.getchannel("A"))
        else:
            background.paste(image.convert("RGB"))
        image = background
    return image


def resized_copy(image: Image.Image, max_width: int) -> Image.Image:
    if image.width <= max_width:
        return image.copy()
    new_height = max(1, round(image.height * max_width / image.width))
    return image.resize((max_width, new_height), Image.Resampling.LANCZOS)


def generated_name(filename: str) -> str:
    digest = hashlib.sha1(filename.encode("utf-8")).hexdigest()[:10]
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(filename).stem).strip("-") or "image"
    return f"{stem}-{digest}.webp"


def process_one(
    item: RemoteImage,
    preview_dir: Path,
    thumb_dir: Path,
    preview_width: int,
    preview_quality: int,
    thumb_width: int,
    thumb_quality: int,
) -> dict[str, str]:
    data = fetch_bytes(item.url, timeout=60, attempts=4)
    name = generated_name(item.filename)
    preview_path = preview_dir / name
    thumb_path = thumb_dir / name

    with Image.open(io.BytesIO(data)) as opened:
        image = prepare_image(opened)
        preview = resized_copy(image, preview_width)
        thumb = resized_copy(image, thumb_width)

        preview.save(preview_path, "WEBP", quality=preview_quality, method=6)
        thumb.save(thumb_path, "WEBP", quality=thumb_quality, method=6)

    return {
        "preview": f"./assets/previews/{name}",
        "thumbnail": f"./assets/thumbs/{name}",
        "caption": item.raw_name.replace("_", " "),
        "date": item.parsed_date.isoformat(timespec="minutes"),
        "month": item.parsed_date.strftime("%B %Y"),
        "filename": item.filename,
    }


def sync_images(site_dir: Path) -> list[dict[str, str]]:
    images = discover_images()

    preview_dir = site_dir / "assets" / "previews"
    thumb_dir = site_dir / "assets" / "thumbs"
    shutil.rmtree(site_dir / "assets" / "images", ignore_errors=True)
    shutil.rmtree(preview_dir, ignore_errors=True)
    shutil.rmtree(thumb_dir, ignore_errors=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir.mkdir(parents=True, exist_ok=True)

    workers = max(1, int(os.getenv("IMAGE_DOWNLOAD_WORKERS", "6")))
    preview_width = max(320, int(os.getenv("PREVIEW_WIDTH", "1920")))
    preview_quality = min(100, max(1, int(os.getenv("PREVIEW_QUALITY", "82"))))
    thumb_width = max(64, int(os.getenv("THUMB_WIDTH", "400")))
    thumb_quality = min(100, max(1, int(os.getenv("THUMB_QUALITY", "78"))))

    print(
        f"[images] Generating Pages copies for {len(images)} originals with {workers} workers "
        f"(preview <= {preview_width}px/q{preview_quality}, thumb <= {thumb_width}px/q{thumb_quality})"
    )

    completed: dict[str, dict[str, str]] = {}
    if images:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    process_one,
                    item,
                    preview_dir,
                    thumb_dir,
                    preview_width,
                    preview_quality,
                    thumb_width,
                    thumb_quality,
                ): item
                for item in images
            }
            for index, future in enumerate(as_completed(futures), start=1):
                item = futures[future]
                try:
                    completed[item.filename] = future.result()
                except Exception as exc:
                    raise RuntimeError(f"Failed to process image {item.filename}: {exc}") from exc
                if index % 25 == 0 or index == len(images):
                    print(f"[images] Processed {index}/{len(images)}")

    manifest = [completed[item.filename] for item in images]

    data_dir = site_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "images.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[images] Wrote data/images.json ({len(manifest)} entries)")
    return manifest


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    sync_images(target)
