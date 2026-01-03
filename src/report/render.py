from __future__ import annotations
from pathlib import Path
import base64

def load_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def b64_png(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii")

def render_report(template: str, report_week: str, blocks_html: str) -> str:
    return (template
            .replace("{{REPORT_WEEK}}", report_week)
            .replace("{{MARKET_BLOCKS}}", blocks_html))
