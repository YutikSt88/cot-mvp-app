from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import zipfile
import pandas as pd

@dataclass(frozen=True)
class ParsedLegacy:
    df: pd.DataFrame
    source_year: int
    source_file: str

def _read_any_csv_like(file_bytes: bytes) -> pd.DataFrame:
    # Most CFTC "deacot" TXT files are CSV-like with headers.
    from io import BytesIO
    bio = BytesIO(file_bytes)
    try:
        return pd.read_csv(bio)
    except Exception:
        bio.seek(0)
        return pd.read_csv(bio, sep=",")

def parse_deacot_zip(zip_path: Path, year: int) -> ParsedLegacy:
    with zipfile.ZipFile(zip_path, "r") as z:
        # find a .txt or .csv inside
        candidates = [n for n in z.namelist() if n.lower().endswith((".txt", ".csv"))]
        if not candidates:
            raise ValueError(f"No .txt/.csv found inside {zip_path.name}")
        name = sorted(candidates)[0]
        raw = z.read(name)
        df = _read_any_csv_like(raw)
        df.columns = [c.strip() for c in df.columns]
        return ParsedLegacy(df=df, source_year=year, source_file=name)
