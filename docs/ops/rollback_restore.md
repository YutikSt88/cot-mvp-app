# Rollback & Restore Guide

Ця інструкція описує, як відкотити проект до стабільної версії v1.1.2 або іншої tagged версії.

---

## Backup

### Створення локального backup'у

Для створення безпечного локального backup'у всього проекту (включаючи незакомічені зміни):

```powershell
# З кореня репозиторію
powershell -ExecutionPolicy Bypass -File scripts\backup_project.ps1
```

### Розташування backup'ів

Backup'и зберігаються в `backups/`:
```
backups/
├── backup_YYYYMMDD_HHMMSS/     # Папка з копією проекту
└── backup_YYYYMMDD_HHMMSS.zip   # ZIP архів
```

### Що включається в backup

- ✓ `configs/` - всі конфігураційні файли
- ✓ `src/` - весь вихідний код
- ✓ `scripts/` - скрипти
- ✓ `docs/` - документація
- ✓ `README.md`, `RELEASES.md`, `requirements.txt`
- ✓ `data/compute/metrics_weekly.parquet`
- ✓ `data/canonical/**` - канонічні дані
- ✓ `data/indicators/**, data/ml/**, data/registry/**`

### Що виключається

- ✗ `.venv/` - віртуальне середовище
- ✗ `__pycache__/` - кеш Python
- ✗ `.git/` - Git репозиторій
- ✗ `data/raw/**` - сирі дані (занадто великі)
- ✗ `backups/` - самі backup'и

### Після створення backup'у

Скрипт виведе зведення з:
- Шляхом до папки backup'у
- Шляхом до ZIP архіву
- Розміром backup'у
- Списком включених/виключених елементів

---

## Safe backup before changes

Перед внесенням змін до compute або UI, створіть backup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backup_project.ps1
```

Backup зберігається в `backups/backup_YYYYMMDD_HHMMSS/` та `backups/backup_YYYYMMDD_HHMMSS.zip`.

---

## Rollback strategy for compute/UI

**Compute rollback:**
- Compute вихідний файл: `data/compute/metrics_weekly.parquet`
- Для відновлення: перезапустити `python -m src.compute.run_compute --root . --log-level INFO`
- Або відновити parquet з backup'у

**UI rollback:**
- UI читає тільки `data/compute/metrics_weekly.parquet` (немає обчислень в UI)
- Зміни UI: тільки файли в `src/app/` (single-file компоненти)
- Для відновлення: відкотити зміни в `src/app/` через Git або backup

---

## Метод A: Git Rollback (рекомендовано)

### Повернення до v1.1.2

```bash
# Перевірка доступних тегів
git tag

# Перехід на tagged версію (detached HEAD)
git checkout v1.1.2

# Або створити нову гілку з tagged версії
git checkout -b restore-v1.1.2 v1.1.2
```

### Повернення на master/main

```bash
# Повернутися на master
git checkout master
# або
git checkout main
```

### Попередження

⚠️ **Важливо:** `data/` не зберігається в Git. Після rollback:
- Дані в `data/` залишаться як є (не відкочаться)
- Якщо потрібен повний rollback з даними — використовуйте Метод B (Backup Restore)

---

## Метод B: Backup Restore (повний rollback)

### Розташування backup'ів

Backup ZIP файли зберігаються в `backups/`:
```
backups/
├── cot-mvp_v1.1.2_20260104_120000.zip
├── cot-mvp_v1.1.2_20260104_180000.zip
└── ...
```

### Процес відновлення

1. **Знайти потрібний backup:**
   ```powershell
   Get-ChildItem backups\cot-mvp_*.zip | Sort-Object LastWriteTime -Descending
   ```

2. **Створити нову папку для відновлення:**
   ```powershell
   # Наприклад
   cd D:\2_Coding\Prodgect_Python
   mkdir cot-mvp-restore
   cd cot-mvp-restore
   ```

3. **Розпакувати backup:**
   ```powershell
   Expand-Archive -Path "..\cot-mvp\backups\cot-mvp_v1.1.2_YYYYMMDD_HHMMSS.zip" -DestinationPath .
   ```

4. **Встановити залежності:**
   ```powershell
   # Створити venv (якщо немає)
   python -m venv .venv
   
   # Активувати venv
   .\.venv\Scripts\Activate.ps1
   
   # Встановити залежності
   pip install -r requirements.txt
   ```

5. **Перевірити відновлення:**
   ```powershell
   # Smoke test
   python -m src.normalize.run_normalize --root . --log-level INFO
   ```

### Налаштування середовища (3-5 команд)

```powershell
# 1. Створити venv
python -m venv .venv

# 2. Активувати venv
.\.venv\Scripts\Activate.ps1

# 3. Оновити pip
python -m pip install --upgrade pip

# 4. Встановити залежності
pip install -r requirements.txt

# 5. Перевірити встановлення
python -c "import pandas; print('OK')"
```

---

## Створення backup'у вручну

Якщо потрібно створити backup поточного стану:

```powershell
# З кореня репозиторію
powershell -ExecutionPolicy Bypass -File scripts\backup_project.ps1

# Або з указанням тегу
powershell -ExecutionPolicy Bypass -File scripts\backup_project.ps1 -Tag "v1.1.2"
```

Backup буде створено в `backups/cot-mvp_<TAG>_<TIMESTAMP>.zip`

---

## Backup v1.1.5

Версія v1.1.5 має git tag `v1.1.5-market-clean` та backup в `backups/backup_20260106_193622/`.

Для відновлення v1.1.5:
1. Використати Git checkout: `git checkout v1.1.5-market-clean`
2. Або скопіювати файли з `backups/backup_20260106_193622/`

## Backup v1.1.4

Версія v1.1.4 має повний backup в `backups/backup_v1.1.4_2026-01-06_1616/` з manifest файлом `BACKUP_MANIFEST.md`.

Для відновлення v1.1.4:
1. Використати Git reset: `git reset --hard 26ada295f74542adc1a67b03cc37529df6168ef5`
2. Або скопіювати файли з `backups/backup_v1.1.4_2026-01-06_1616/`

---

## Відновлення даних після rollback

Після rollback дані в `data/` залишаться як є. Для повного відновлення даних:

1. **Видалити старі дані:**
   ```powershell
   Remove-Item -Recurse -Force data\
   ```

2. **Запустити pipeline заново:**
   ```powershell
   python -m src.ingest.run_ingest --log-level INFO
   python -m src.normalize.run_normalize --root . --log-level INFO
   python -m src.registry.run_registry --log-level INFO
   ```

---

## Перевірка версії

```bash
# Перевірити поточний commit
git log --oneline -1

# Перевірити теги на поточному commit
git describe --tags

# Перевірити всі теги
git tag
```




