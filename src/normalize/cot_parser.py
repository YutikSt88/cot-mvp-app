from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import zipfile
import pandas as pd
from io import BytesIO


@dataclass(frozen=True)
class ParsedLegacy:
    df: pd.DataFrame
    source_year: int
    source_file: str


def parse_deacot_zip(zip_path: Path, year: int) -> ParsedLegacy:
    """
    Parse annual.txt from COT ZIP archive.
    
    Reads annual.txt specifically (comma-separated, UTF-8 encoding).
    """
    with zipfile.ZipFile(zip_path, "r") as z:
        # Look for annual.txt specifically
        if "annual.txt" not in z.namelist():
            raise ValueError(f"annual.txt not found inside {zip_path.name}")
        
        raw = z.read("annual.txt")
        bio = BytesIO(raw)
        df = pd.read_csv(bio, encoding="utf-8", delimiter=",")
        df.columns = [c.strip() for c in df.columns]
        return ParsedLegacy(df=df, source_year=year, source_file="annual.txt")
