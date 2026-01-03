from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

@dataclass(frozen=True)
class DownloadResult:
    path: Path
    size_bytes: int
    downloaded_at_utc: str

@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=10))
def download_file(url: str, out_path: Path, timeout_s: int = 60) -> DownloadResult:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    r = requests.get(url, stream=True, timeout=timeout_s)
    r.raise_for_status()

    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    size = 0
    with tmp.open("wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 256):
            if chunk:
                f.write(chunk)
                size += len(chunk)

    tmp.replace(out_path)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return DownloadResult(path=out_path, size_bytes=size, downloaded_at_utc=ts)
