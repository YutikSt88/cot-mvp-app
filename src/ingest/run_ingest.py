from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from src.common.dates import year_range
from src.common.logging import setup_logging
from src.common.paths import ProjectPaths
from src.ingest.cftc_downloader import download_file
from src.ingest.manifest import ManifestRow, append_manifest, load_manifest, sha256_file


def _utc_now_ts() -> str:
    # canonical timestamp format: YYYYMMDD_HHMMSS
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _parse_utc(s: str):
    # robust parse; returns pandas Timestamp or NaT
    return pd.to_datetime(s, errors="coerce", utc=True)


def _get_last_ok_row(manifest: pd.DataFrame, dataset: str, year: int) -> dict | None:
    df = manifest[(manifest["dataset"] == dataset) & (manifest["year"] == year) & (manifest["status"] == "OK")]
    if df.empty:
        return None

    ts = _parse_utc(df["downloaded_at_utc"])
    if ts.isna().all():
        # fallback: last row as it appears
        row = df.iloc[-1]
        return row.to_dict()

    idx = ts.idxmax()
    return df.loc[idx].to_dict()


def _is_canonical_raw_path(dataset: str, year: int, raw_path: str) -> bool:
    # canonical layout:
    # data/raw/<dataset>/<year>/deacot<year>__YYYYMMDD_HHMMSS.zip
    # raw_path is relative to project root
    norm = raw_path.replace("\\", "/")
    prefix = f"data/raw/{dataset}/{year}/deacot{year}__"
    return norm.startswith(prefix) and norm.endswith(".zip")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".", help="project root")
    p.add_argument("--start-year", type=int, default=2016)
    p.add_argument("--end-year", type=int, default=None)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    logger = setup_logging(args.log_level)
    paths = ProjectPaths(Path(args.root).resolve())

    cfg = yaml.safe_load((paths.configs / "markets.yaml").read_text(encoding="utf-8"))
    url_tpl = cfg["source"]["cftc_historical_zip_url_template"]
    dataset = cfg["source"]["dataset"]

    current_year = datetime.now(timezone.utc).year
    refresh_years = {current_year, current_year - 1}

    end_year = args.end_year or current_year
    years = year_range(args.start_year, end_year)

    manifest_path = paths.raw / "manifest.csv"
    manifest = load_manifest(manifest_path)

    for y in years:
        url = url_tpl.format(year=y)
        last_ok = _get_last_ok_row(manifest, dataset, y)

        is_historical = y < (current_year - 1)
        is_refresh = y in refresh_years

        # canonical snapshot path (new standard)
        out_dir = paths.raw / dataset / f"{y}"
        snap_ts = _utc_now_ts()
        final_out = out_dir / f"deacot{y}__{snap_ts}.zip"

        # -----------------------------
        # A) HISTORICAL YEARS
        # -----------------------------
        if is_historical and last_ok is not None:
            # If last OK is already canonical -> true skip-only
            if _is_canonical_raw_path(dataset, y, str(last_ok.get("raw_path", ""))):
                logger.info(f"[ingest] skip year={y} (historical)")
                continue

            # One-time storage migration (NO download):
            # copy existing flat/legacy OK zip into canonical snapshot and record OK
            try:
                prev_rel = str(last_ok.get("raw_path", ""))
                prev_abs = paths.root / prev_rel
                if not prev_abs.exists():
                    logger.warning(f"[ingest] historical year={y}: last_ok.raw_path missing on disk -> will download")
                else:
                    _ensure_parent(final_out)
                    shutil.copy2(prev_abs, final_out)
                    h = sha256_file(final_out)
                    size_bytes = final_out.stat().st_size

                    append_manifest(
                        manifest_path,
                        ManifestRow(
                            dataset=dataset,
                            year=y,
                            url=str(last_ok.get("url", url)),
                            downloaded_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                            raw_path=str(final_out.relative_to(paths.root)),
                            sha256=h,
                            size_bytes=size_bytes,
                            status="OK",
                            error="",
                        ),
                    )
                    manifest = load_manifest(manifest_path)
                    logger.info(f"[ingest] migrated year={y} -> OK snapshot={final_out.name} bytes={size_bytes}")
                    continue
            except Exception as e:
                append_manifest(
                    manifest_path,
                    ManifestRow(
                        dataset=dataset,
                        year=y,
                        url=url,
                        downloaded_at_utc="",
                        raw_path="",
                        sha256="",
                        size_bytes=0,
                        status="ERROR",
                        error=str(e)[:500],
                    ),
                )
                manifest = load_manifest(manifest_path)
                logger.error(f"[ingest] ERROR year={y} (historical migrate): {e}")
                continue

        # If historical and no OK yet -> bootstrap download (normal OK snapshot)
        # (falls through to download section below)

        # -----------------------------
        # B) REFRESH YEARS
        # -----------------------------
        if is_refresh:
            # Always check refresh years: download temp, hash-compare vs last OK
            tmp_path = final_out.with_suffix(final_out.suffix + ".tmp")
            _ensure_parent(tmp_path)

            try:
                logger.info(f"[ingest] downloading year={y} url={url} -> temp={tmp_path.name}")
                res = download_file(url, tmp_path)

                new_sha = sha256_file(tmp_path)
                old_sha = str(last_ok.get("sha256")) if last_ok is not None else None

                # If last OK exists but is NOT canonical, we force creating a new OK snapshot
                # to migrate into the new layout (even if sha is the same).
                force_new_ok = last_ok is not None and not _is_canonical_raw_path(
                    dataset, y, str(last_ok.get("raw_path", ""))
                )

                if (old_sha is not None) and (new_sha == old_sha) and (not force_new_ok):
                    # UNCHANGED: keep audit link to last OK snapshot
                    last_ok_raw_path = str(last_ok.get("raw_path", ""))
                    size_bytes = 0
                    try:
                        p_abs = paths.root / last_ok_raw_path
                        if p_abs.exists():
                            size_bytes = p_abs.stat().st_size
                    except Exception:
                        size_bytes = 0

                    append_manifest(
                        manifest_path,
                        ManifestRow(
                            dataset=dataset,
                            year=y,
                            url=url,
                            downloaded_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                            raw_path=last_ok_raw_path,
                            sha256=new_sha,
                            size_bytes=size_bytes,
                            status="UNCHANGED",
                            error="",
                        ),
                    )
                    # delete temp snapshot (immutability: do not keep duplicate)
                    try:
                        tmp_path.unlink(missing_ok=True)
                    except Exception:
                        pass

                    manifest = load_manifest(manifest_path)
                    logger.info(f"[ingest] unchanged year={y} (same sha256) -> raw_path={last_ok_raw_path}")
                    continue

                # Different hash (or forced migration) -> commit new immutable snapshot
                _ensure_parent(final_out)
                tmp_path.replace(final_out)

                size_bytes = final_out.stat().st_size
                append_manifest(
                    manifest_path,
                    ManifestRow(
                        dataset=dataset,
                        year=y,
                        url=url,
                        downloaded_at_utc=res.downloaded_at_utc,
                        raw_path=str(final_out.relative_to(paths.root)),
                        sha256=new_sha,
                        size_bytes=size_bytes,
                        status="OK",
                        error="",
                    ),
                )
                manifest = load_manifest(manifest_path)
                logger.info(f"[ingest] ok year={y} bytes={size_bytes} sha256={new_sha[:12]} snapshot={final_out.name}")
                continue

            except Exception as e:
                # cleanup temp
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass

                append_manifest(
                    manifest_path,
                    ManifestRow(
                        dataset=dataset,
                        year=y,
                        url=url,
                        downloaded_at_utc="",
                        raw_path="",
                        sha256="",
                        size_bytes=0,
                        status="ERROR",
                        error=str(e)[:500],
                    ),
                )
                manifest = load_manifest(manifest_path)
                logger.error(f"[ingest] ERROR year={y} (refresh): {e}")
                continue

        # -----------------------------
        # C) BOOTSTRAP (non-refresh years without OK)
        # -----------------------------
        # For years that are not in refresh window:
        # - if no OK yet -> download and create canonical OK snapshot
        # - if OK exists (should have been handled above for historical) -> skip
        if last_ok is not None:
            # non-refresh + has OK (e.g., future range) -> skip
            logger.info(f"[ingest] skip year={y} (already OK)")
            continue

        tmp_path = final_out.with_suffix(final_out.suffix + ".tmp")
        _ensure_parent(tmp_path)
        try:
            logger.info(f"[ingest] downloading year={y} url={url} -> temp={tmp_path.name}")
            res = download_file(url, tmp_path)

            new_sha = sha256_file(tmp_path)
            _ensure_parent(final_out)
            tmp_path.replace(final_out)

            size_bytes = final_out.stat().st_size
            append_manifest(
                manifest_path,
                ManifestRow(
                    dataset=dataset,
                    year=y,
                    url=url,
                    downloaded_at_utc=res.downloaded_at_utc,
                    raw_path=str(final_out.relative_to(paths.root)),
                    sha256=new_sha,
                    size_bytes=size_bytes,
                    status="OK",
                    error="",
                ),
            )
            manifest = load_manifest(manifest_path)
            logger.info(f"[ingest] ok year={y} bytes={size_bytes} snapshot={final_out.name}")
        except Exception as e:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

            append_manifest(
                manifest_path,
                ManifestRow(
                    dataset=dataset,
                    year=y,
                    url=url,
                    downloaded_at_utc="",
                    raw_path="",
                    sha256="",
                    size_bytes=0,
                    status="ERROR",
                    error=str(e)[:500],
                ),
            )
            manifest = load_manifest(manifest_path)
            logger.error(f"[ingest] ERROR year={y}: {e}")


if __name__ == "__main__":
    main()
