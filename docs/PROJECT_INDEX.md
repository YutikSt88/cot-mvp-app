# Project Index — COT-MVP

## Frozen (Do Not Touch)
- `src/ingest/` — Data ingestion pipeline
- `src/normalize/` — Data normalization pipeline
- `app.py` — Root entrypoint for Streamlit Cloud

## Source of Truth
- `data/compute/metrics_weekly.parquet` — Computed metrics dataset (144 columns)

## Main Commands (Windows)

### Weekly Pipeline
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_weekly.ps1
```
Runs: ingest → normalize → compute

### Deploy to Streamlit Cloud
```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_to_github.ps1
```
Builds deploy package, runs smoke tests, pushes to GitHub

### Build Deploy Package
```bash
python scripts/build_deploy_package.py
```

### Smoke Test
```bash
python scripts/smoke_test_deploy.py
```

## Key Directories

- `src/compute/` — Metrics & analytics logic
- `src/app/` — Streamlit pages & components
- `scripts/` — Automation (build / smoke / deploy)
- `configs/` — Markets & configuration
- `data/` — Data storage (raw, canonical, compute, ml, registry)
- `docs/` — Documentation

## Pipeline Flow

```
ingest → normalize → compute → Streamlit deploy
```

## Deployment

- **Deploy repo:** `YutikSt88/cot-mvp-app` (GitHub)
- **Streamlit Cloud:** `cot-app.streamlit.app`
- **Main file:** `app.py` (root entrypoint)

## Documentation

- `README.md` — Full project documentation
- `docs/ARCHITECTURE_OVERVIEW.md` — Architecture overview for new developers
- `docs/DEPLOY_STREAMLIT.md` — Deployment instructions
- `docs/BACKUP.md` — Backup & rollback procedures
- `RELEASES.md` — Release history
