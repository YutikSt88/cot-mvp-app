# Backup and Release Management

This document describes how to create backups and tag releases for COT-MVP.

## Creating a Backup

Use the backup script to create a zip archive of the project:

```bash
python scripts/backup_release.py
```

This creates a zip file in `backups/` with timestamp:
- `backups/cot-mvp_v0.2_YYYYMMDD_HHMM.zip`

### Including Data Files

To include data files (metrics_weekly.parquet, canonical parquet):

```bash
python scripts/backup_release.py --with-data
```

**Note:** Data files can be large. Use `--with-data` only when you need a complete backup.

### What's Included

- `src/` - All source code
- `configs/` - Configuration files
- `README.md`, `RELEASES.md` - Documentation
- `pyproject.toml`, `requirements*.txt` - Dependencies
- `.gitignore` - Git ignore rules
- Optionally: `data/compute/metrics_weekly.parquet` and `data/canonical/cot_weekly_canonical_full.parquet`

### What's Excluded

- `.venv/` - Virtual environment
- `__pycache__/` - Python cache
- `.git/` - Git repository
- `data/raw/` - Raw data snapshots
- `data/tmp/` - Temporary files

## Tagging a Release

After making changes and creating a backup, tag the release:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/tag_release.ps1
```

This script:
1. Checks for uncommitted changes
2. Stages all changes (`git add -A`)
3. Creates a commit with message: `v0.2: week navigator + OI tab polish + backups`
4. Creates an annotated tag: `v0.2`

If there are no changes, the script exits cleanly without creating a commit.

### Manual Git Commands

If you prefer to do it manually:

```bash
git status
git add -A
git commit -m "v0.2: week navigator + OI tab polish + backups"
git tag -a v0.2 -m "v0.2 release"
```

### Pushing to Remote

The script does NOT push to remote. To push:

```bash
git push origin main
git push origin v0.2
```

## Version History

- **v0.2**: Week navigator + OI tab polish + backups
- **v0.1**: Initial MVP release


