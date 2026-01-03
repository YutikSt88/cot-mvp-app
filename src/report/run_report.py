from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # deterministic, no GUI backend
import matplotlib.pyplot as plt


# --- Paths (contract) ---
INDICATORS_PATH = Path("data/indicators/indicators_weekly.parquet")
SIGNAL_STATUS_PATH = Path("data/indicators/signal_status.parquet")
TEMPLATE_PATH = Path("src/report/template.html")
REPORTS_ROOT = Path("reports")

# --- MVP markets (contract) ---
MARKETS = ["EUR", "GBP", "GOLD", "JPY"]

MARKET_TITLES = {
    "EUR": "EUR Futures",
    "GBP": "GBP Futures",
    "JPY": "JPY Futures",
    "GOLD": "Gold",
}


@dataclass(frozen=True)
class MarketBlock:
    market_key: str
    report_week: str
    status: str
    reason_code: str
    key_numbers_html: str
    chart_base64_png: str


def _read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input file: {path}")
    return pd.read_parquet(path)


def _iso_date_series(s: pd.Series) -> pd.Series:
    # Ensure date-like values are normalized as YYYY-MM-DD strings
    dt = pd.to_datetime(s).dt.date
    return dt.astype(str)


def _format_int(x) -> str:
    if pd.isna(x):
        return "—"
    try:
        return f"{int(x):,}"
    except Exception:
        return str(x)


def _format_float(x, digits: int = 2) -> str:
    if pd.isna(x):
        return "—"
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return str(x)


def _format_pct(x, digits: int = 2) -> str:
    # Input expected as fraction or percent? Contract says it's already a metric column.
    # We DO NOT reinterpret; we display as-is with percent sign.
    if pd.isna(x):
        return "—"
    try:
        return f"{float(x):.{digits}f}%"
    except Exception:
        return str(x)


def _make_funds_net_chart_base64(df_market: pd.DataFrame, market_key: str) -> str:
    """
    Line chart: report_date (x) vs funds_net (y).
    Deterministic output: fixed size, dpi, style.
    Returns base64 PNG (no new files needed).
    """
    df = df_market.copy()
    df["report_date"] = pd.to_datetime(df["report_date"])
    df = df.sort_values("report_date")

    # Deterministic matplotlib settings
    plt.close("all")
    fig = plt.figure(figsize=(8.8, 2.8), dpi=140)
    ax = fig.add_subplot(111)

    ax.plot(df["report_date"], df["funds_net"], linewidth=2.0)
    ax.set_title(f"{MARKET_TITLES.get(market_key, market_key)} — Funds Net over time", fontsize=10)
    ax.set_xlabel("report_date", fontsize=9)
    ax.set_ylabel("funds_net", fontsize=9)

    # Minimal, readable ticks
    ax.tick_params(axis="both", labelsize=8)
    fig.autofmt_xdate(rotation=0)

    ax.grid(True, alpha=0.25)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)

    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return b64


def _key_numbers_table_html(row: pd.Series) -> str:
    # Only fields requested by MVP
    funds_net = _format_int(row.get("funds_net"))
    funds_net_chg = _format_int(row.get("funds_net_chg"))
    open_interest = _format_int(row.get("open_interest"))
    oi_chg = _format_int(row.get("oi_chg"))
    funds_net_pct_oi = row.get("funds_net_pct_oi")

    # Display funds_net_pct_oi as percent string; do not change semantics.
    funds_net_pct_oi_str = _format_pct(funds_net_pct_oi, digits=2)

    return f"""
      <table>
        <tr><td>Funds Net</td><td><b>{funds_net}</b></td></tr>
        <tr><td>Funds Net Change (WoW)</td><td>{funds_net_chg}</td></tr>
        <tr><td>Open Interest</td><td>{open_interest}</td></tr>
        <tr><td>Open Interest Change</td><td>{oi_chg}</td></tr>
        <tr><td>Funds Net % of OI</td><td>{funds_net_pct_oi_str}</td></tr>
      </table>
    """.strip()


def _render_market_section(block: MarketBlock) -> str:
    status_class = "active" if block.status == "ACTIVE" else "pause"
    reason = block.reason_code if block.reason_code else "—"

    return f"""
    <section class="market" id="market-{block.market_key}">
      <h2>{MARKET_TITLES.get(block.market_key, block.market_key)}</h2>
      <div class="row">
        <div class="col">
          <div class="status {status_class}">
            {block.status}
            <small>reason_code: <b>{reason}</b></small>
          </div>
          {block.key_numbers_html}
        </div>
        <div class="col chart">
          <img alt="Funds Net chart for {block.market_key}"
               src="data:image/png;base64,{block.chart_base64_png}" />
        </div>
      </div>
    </section>
    """.strip()


def _load_template() -> str:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Missing template: {TEMPLATE_PATH}")
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def run() -> Path:
    # 1) Load data
    ind = _read_parquet(INDICATORS_PATH)
    sig = _read_parquet(SIGNAL_STATUS_PATH)

    # 2) Normalize dates to stable string form for joins/filters
    ind = ind.copy()
    sig = sig.copy()

    ind["report_date"] = _iso_date_series(ind["report_date"])
    sig["report_date"] = _iso_date_series(sig["report_date"])

    # 3) Determine report week (contract)
    report_week = str(ind["report_date"].max())

    # 4) Filter to report week for key numbers/status join
    ind_week = ind[ind["report_date"] == report_week].copy()
    sig_week = sig[sig["report_date"] == report_week].copy()

    # Defensive: ensure one row per market
    # (contract says no duplicates, but we fail loudly if violated)
    if ind_week.duplicated(subset=["market_key", "report_date"]).any():
        raise ValueError("Duplicate rows found in indicators_weekly for report week.")
    if sig_week.duplicated(subset=["market_key", "report_date"]).any():
        raise ValueError("Duplicate rows found in signal_status for report week.")

    # 5) Build market blocks
    blocks: List[MarketBlock] = []
    for m in MARKETS:
        # indicators row (must exist)
        row_ind = ind_week[ind_week["market_key"] == m]
        if row_ind.empty:
            raise ValueError(f"Missing indicators row for market={m} report_date={report_week}")
        row_ind = row_ind.iloc[0]

        # signal row (must exist)
        row_sig = sig_week[sig_week["market_key"] == m]
        if row_sig.empty:
            raise ValueError(f"Missing signal row for market={m} report_date={report_week}")
        row_sig = row_sig.iloc[0]

        status = str(row_sig.get("status"))
        reason_code = str(row_sig.get("reason_code", "")) if not pd.isna(row_sig.get("reason_code", "")) else ""

        # chart uses full history up to report_week
        df_hist = ind[(ind["market_key"] == m) & (ind["report_date"] <= report_week)][
            ["report_date", "funds_net"]
        ].copy()
        if df_hist.empty:
            raise ValueError(f"No history available for market={m} up to report_date={report_week}")

        chart_b64 = _make_funds_net_chart_base64(df_hist, market_key=m)
        key_numbers_html = _key_numbers_table_html(row_ind)

        blocks.append(
            MarketBlock(
                market_key=m,
                report_week=report_week,
                status=status,
                reason_code=reason_code,
                key_numbers_html=key_numbers_html,
                chart_base64_png=chart_b64,
            )
        )

    # 6) Render HTML
    template = _load_template()
    market_sections = "\n\n".join(_render_market_section(b) for b in blocks)

    html = (
        template.replace("{{REPORT_WEEK}}", report_week)
                .replace("{{MARKET_SECTIONS}}", market_sections)
    )

    # 7) Write output (contract path)
    out_dir = REPORTS_ROOT / report_week
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{report_week}_weekly_cot_report.html"
    out_path.write_text(html, encoding="utf-8")

    return out_path


if __name__ == "__main__":
    path = run()
    print(f"OK: wrote {path}")
