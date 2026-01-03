from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import pandas as pd

MANIFEST_COLUMNS = [
    "dataset", "year", "url", "downloaded_at_utc",
    "raw_path", "sha256", "size_bytes", "status", "error"
]

@dataclass
class ManifestRow:
    dataset: str
    year: int
    url: str
    downloaded_at_utc: str
    raw_path: str
    sha256: str
    size_bytes: int
    status: str
    error: str = ""

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_manifest(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=MANIFEST_COLUMNS)

def append_manifest(path: Path, row: ManifestRow) -> None:
    df = load_manifest(path)
    df = pd.concat([df, pd.DataFrame([row.__dict__])], ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
