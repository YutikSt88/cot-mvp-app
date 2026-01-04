# Rollback & Restore Guide

Ця інструкція описує, як відкотити проект до стабільної версії v1.1.2 або іншої tagged версії.

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

