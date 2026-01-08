# Windows Task Scheduler Setup for Weekly COT Pipeline

Цей документ описує кроки налаштування автоматичного щотижневого запуску COT pipeline через Windows Task Scheduler.

## Розклад

- **Частота:** Щотижня
- **День:** Субота
- **Час:** 08:00 (локальний час)

## Передумови

1. Проект встановлено локально (наприклад: `D:\2_Coding\Prodgect_Python\cot-mvp`)
2. Python встановлено та доступний через PATH (або віртуальне середовище `.venv` створено)
3. Всі залежності встановлені (`pip install -r requirements.txt`)
4. PowerShell доступний (стандартно в Windows)

## Крок за кроком

### 1. Відкрити Task Scheduler

1. Натисніть `Win + R`
2. Введіть `taskschd.msc` та натисніть Enter
3. Або знайдіть "Task Scheduler" через Start Menu

### 2. Створити нову задачу

1. У правій панелі натисніть **"Create Task"** (НЕ "Create Basic Task")
   - "Create Basic Task" має обмежені можливості
   - "Create Task" дає повний контроль

### 3. Загальні налаштування (General tab)

1. **Name:** `COT Weekly Pipeline`
2. **Description:** `Automated weekly COT data pipeline: ingest → normalize → registry → ml_backup`
3. **Security options:**
   - Виберіть **"Run whether user is logged on or not"** (рекомендовано)
   - Або **"Run only when user is logged on"** (для тестування)
4. **Configure for:** Windows 10 (або ваша версія)
5. **Run with highest privileges:** (за потреби, якщо є проблеми з правами)

### 4. Тригери (Triggers tab)

1. Натисніть **"New..."**
2. **Begin the task:** `On a schedule`
3. **Settings:**
   - **Weekly**
   - **Start:** `08:00:00` (або інший час)
   - **Recur every:** `1` weeks
   - **On:** `Saturday` (відмітити)
4. Натисніть **OK**

### 5. Дії (Actions tab)

1. Натисніть **"New..."**
2. **Action:** `Start a program`
3. **Program/script:** 
   ```
   powershell.exe
   ```
4. **Add arguments (optional):**
   ```
   -NoProfile -ExecutionPolicy Bypass -File "D:\2_Coding\Prodgect_Python\cot-mvp\scripts\run_weekly.ps1"
   ```
   ⚠️ **Важливо:** Замініть `D:\2_Coding\Prodgect_Python\cot-mvp` на ваш шлях до проекту!
5. **Start in (optional):**
   ```
   D:\2_Coding\Prodgect_Python\cot-mvp
   ```
   (замініть на ваш шлях)
6. Натисніть **OK**

### 6. Умови (Conditions tab) - опційно

1. **Power:**
   - ✅ Відмітити **"Start the task only if the computer is on AC power"** (якщо ноутбук)
   - Або залишити відмітку знятою (для десктопу)
2. **Network:**
   - Можна відмітити **"Start only if the following network connection is available"** (якщо потрібен інтернет)

### 7. Налаштування (Settings tab)

1. **Allow task to be run on demand:** ✅ (для ручного тестування)
2. **Run task as soon as possible after a scheduled start is missed:** ✅ (рекомендовано)
3. **If the task fails, restart every:** (за потреби, за замовчуванням не встановлено)
4. **Stop the task if it runs longer than:** (опційно, наприклад 2 години)

### 8. Збереження

1. Натисніть **OK**
2. Можливо потрібно ввести пароль користувача (якщо вибрано "Run whether user is logged on or not")

## Тестування

### Ручний запуск через Task Scheduler

1. Відкрийте Task Scheduler
2. Знайдіть задачу `COT Weekly Pipeline` у списку
3. Клацніть правою кнопкою → **"Run"**
4. Перевірте статус (колонка "Last Run Result" повинна показати "0x0" = success)
5. Перевірте логи (див. нижче)

### Ручний запуск через PowerShell

Відкрийте PowerShell і виконайте:

```powershell
cd D:\2_Coding\Prodgect_Python\cot-mvp
.\scripts\run_weekly.ps1
```

Або з будь-якої директорії:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\2_Coding\Prodgect_Python\cot-mvp\scripts\run_weekly.ps1"
```

## Перевірка логів

### Логи скрипта автоматизації

**Розташування:** `logs/weekly_run_YYYYMMDD_HHMMSS.log`

Приклад:
```
logs/weekly_run_20260104_080015.log
```

**Що містить:**
- Таймстемпи кожного кроку
- Вивід команд pipeline (stdout/stderr)
- Статус завершення (DONE або FAILED)
- Помилки (якщо є)

### Логи pipeline (додаткові)

Pipeline також пише власні логи через Python logging. Перевірте:
- Консольний вивід (якщо запускали вручну)
- Файли `*.log` у корені проекту (якщо налаштовано)

## Усунення проблем

### Задача не запускається

1. Перевірте права доступу користувача
2. Перевірте, що PowerShell доступний: `powershell.exe -Version`
3. Перевірте шлях до скрипта (використовуйте абсолютний шлях)
4. Перевірте логи Task Scheduler: Task Scheduler → Task Scheduler Library → ваша задача → History tab

### Скрипт падає з помилкою

1. Запустіть скрипт вручну через PowerShell для детальних помилок
2. Перевірте `logs/weekly_run_*.log`
3. Перевірте, що Python доступний: `python --version`
4. Перевірте, що віртуальне середовище активовано (або Python в PATH)
5. Перевірте, що всі залежності встановлені

### Permission denied

1. Перевірте права на папку проекту
2. Запустіть Task Scheduler як адміністратор для створення задачі
3. Перевірте "Run with highest privileges" у General tab

## Налаштування для іншого розкладу

Для зміни частоти/часу:
1. Відкрийте задачу
2. Triggers tab → Edit
3. Змініть день/час
4. OK

## Видалення задачі

1. Task Scheduler → знайдіть `COT Weekly Pipeline`
2. Клацніть правою кнопкою → Delete
3. Підтвердіть

---

**Останнє оновлення:** 2026-01-04









