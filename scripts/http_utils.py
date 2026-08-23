from __future__ import annotations

import time
import urllib.error
import urllib.request

USER_AGENT = "G2ClassicRevived-GitHubPages-Builder/1.0"


def fetch_bytes(url: str, *, timeout: int = 30, attempts: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(min(2 ** (attempt - 1), 4))
    assert last_error is not None
    raise last_error


def fetch_text(url: str, *, timeout: int = 30, attempts: int = 3) -> str:
    return fetch_bytes(url, timeout=timeout, attempts=attempts).decode("utf-8", errors="replace")
