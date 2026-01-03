# COT-MVP: Commitment of Traders Data Processing Pipeline

## 📋 Огляд

**COT-MVP** — це система обробки та аналізу тижневих звітів Commitment of Traders (COT) від CFTC (Commodity Futures Trading Commission). Проект завантажує історичні дані COT, нормалізує їх, розраховує індикатори, генерує торгові сигнали та створює HTML-звіти для аналізу позицій інституційних трейдерів.

### Основні можливості

- ✅ Автоматичне завантаження COT даних з CFTC
- ✅ Нормалізація та валідація даних з QA перевірками
- ✅ Розрахунок індикаторів на основі Non-Commercial позицій (Funds)
- ✅ Генерація торгових сигналів (ACTIVE/PAUSE)
- ✅ Створення HTML-звітів з графіками та метриками
- ✅ ML-ready датасет для незалежного використання

### Підтримувані ринки

- **EUR** (EURO FX - CME) - Contract Code: 099741
- **JPY** (JAPANESE YEN - CME) - Contract Code: 097741
- **GBP** (BRITISH POUND - CME) - Contract Code: 096742
- **GOLD** (GOLD - COMEX) - Contract Code: 088691

---

## 🏗 Архітектура Pipeline

Проект реалізує чіткий ETL pipeline з 4 основними етапами:

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│   INGEST    │ --> │  NORMALIZE   │ --> │  INDICATORS  │ --> │   REPORT    │
│             │     │              │     │              │     │             │
│ Завантаження│     │ Нормалізація │     │ Індикатори   │     │ HTML-звіти  │
│ ZIP з CFTC  │     │ + QA         │     │ + Сигнали    │     │             │
└─────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
                           │
                           │
                           ▼
                    ┌──────────────┐
                    │  ML BACKUP   │
                    │              │
                    │ ML датасет   │
                    └──────────────┘
```

### Етапи Pipeline

1. **INGEST** (`src/ingest/`)
   - Завантажує ZIP-архіви з CFTC за роками
   - Використовує manifest для відстеження завантажень
   - Розумно оновлює дані (refresh для поточного/минулого року)

2. **NORMALIZE** (`src/normalize/`)
   - Парсить `annual.txt` з ZIP-архівів
   - Фільтрує ринки через whitelist contract codes
   - Створює canonical dataset з усіма групами трейдерів
   - Виконує QA перевірки (blocking)

3. **INDICATORS** (`src/indicators/`)
   - Розраховує індикатори на основі Non-Commercial позицій
   - Обчислює WoW зміни та нормалізації
   - Генерує торгові сигнали (ACTIVE/PAUSE)

4. **REPORT** (`src/report/`)
   - Генерує HTML-звіти з графіками та метриками
   - Показує статус сигналів для кожного ринку

5. **ML BACKUP** (`src/normalize/run_ml_backup.py`)
   - Створює очищений датасет для ML
   - Виключає технічні колонки (raw_source_*)

---

## 📁 Структура проекту

```
cot-mvp/
├── configs/
│   └── markets.yaml              # Конфігурація ринків (contract codes)
│
├── data/
│   ├── raw/                      # Сирі ZIP-архіви з CFTC
│   │   ├── legacy_futures_only/
│   │   │   ├── 2011/...2025/    # Snapshots за роками
│   │   │   └── manifest.csv      # Реєстр завантажень
│   │
│   ├── canonical/                # Нормалізований датасет
│   │   ├── cot_weekly_canonical.parquet
│   │   └── qa_report.txt
│   │
│   ├── indicators/               # Розраховані індикатори
│   │   ├── indicators_weekly.parquet
│   │   └── signal_status.parquet
│   │
│   ├── ml/                       # ML-ready датасет
│   │   ├── cot_weekly_ml.parquet
│   │   └── cot_weekly_ml.csv
│   │
│   └── registry/                 # (для майбутнього використання)
│
├── reports/                      # HTML-звіти
│   └── YYYY-MM-DD/
│       └── YYYY-MM-DD_weekly_cot_report.html
│
├── src/
│   ├── common/                   # Спільні утиліти
│   │   ├── dates.py             # Функції для роботи з датами
│   │   ├── logging.py           # Налаштування логування
│   │   └── paths.py             # ProjectPaths dataclass
│   │
│   ├── ingest/                   # Модуль завантаження
│   │   ├── run_ingest.py        # Головний runner
│   │   ├── cftc_downloader.py   # Завантаження з CFTC
│   │   └── manifest.py          # Робота з manifest
│   │
│   ├── normalize/                # Модуль нормалізації
│   │   ├── run_normalize.py     # Головний runner
│   │   ├── cot_parser.py        # Парсинг annual.txt
│   │   ├── qa_checks.py         # QA перевірки
│   │   ├── run_ml_backup.py     # ML backup generator
│   │   └── canonical_schema.py  # (legacy schema reference)
│   │
│   ├── indicators/               # Модуль індикаторів
│   │   ├── run_indicators.py    # Головний runner
│   │   ├── cot_indicators.py    # Розрахунок індикаторів
│   │   └── signal_rules.py      # Правила сигналів
│   │
│   └── report/                   # Модуль звітів
│       ├── run_report.py        # Головний runner
│       ├── render.py            # Рендеринг HTML
│       └── template.html        # HTML шаблон
│
├── docs/                         # Документація
│   └── CR-001_refresh_window.md
│
├── requirements.txt              # Python залежності
└── README.md                     # Цей файл
```

---

## 🔄 Детальний Pipeline

### 1. INGEST (`src/ingest/run_ingest.py`)

**Призначення:** Завантаження ZIP-архівів COT даних з CFTC

**Вхідні дані:**
- URL template з `configs/markets.yaml`
- `data/raw/manifest.csv` (реєстр завантажень)

**Процес:**
1. Читає manifest для відстеження завантажених файлів
2. Для кожного року:
   - **Historical years** (старіші за поточний-1): skip якщо вже є OK snapshot
   - **Refresh years** (поточний та поточний-1): завантажує, перевіряє SHA256, створює snapshot якщо змінився
   - **Bootstrap years** (інші): завантажує вперше
3. Зберігає snapshots у канонічному форматі: `data/raw/{dataset}/{year}/deacot{year}__{timestamp}.zip`
4. Оновлює manifest з статусами (OK, ERROR, UNCHANGED)

**Вихідні дані:**
- ZIP-файли в `data/raw/legacy_futures_only/{year}/`
- Оновлений `data/raw/manifest.csv`

**Ключові файли:**
- `run_ingest.py` - головна логіка
- `cftc_downloader.py` - HTTP завантаження з retry
- `manifest.py` - робота з manifest (load, append, SHA256)

---

### 2. NORMALIZE (`src/normalize/run_normalize.py`)

**Призначення:** Нормалізація сирих даних у canonical формат

**Вхідні дані:**
- ZIP-файли з `data/raw/manifest.csv` (тільки статус OK)
- Конфігурація ринків з `configs/markets.yaml`

**Процес:**
1. **Selection:** Читає manifest, обирає latest OK snapshot per year
2. **Parsing:** Для кожного ZIP:
   - Відкриває `annual.txt` з ZIP
   - Читає CSV через `pd.read_csv`
   - Фільтрує по contract codes з whitelist
   - Мапить contract_code → market_key
3. **Transformation:**
   - Вибирає потрібні колонки (позиції Long/Short для всіх груп трейдерів)
   - Розраховує net позиції (comm_net, noncomm_net, nonrept_net)
   - Нормалізує типи (date, numeric, string)
4. **QA (blocking):**
   - Uniqueness: (market_key, report_date) без дублів
   - Whitelist integrity: тільки дозволені market_key та contract_code
   - Null ratio: <= 0.1% для numeric колонок
   - Open interest non-negative
5. **Output:** Записує canonical parquet тільки якщо QA = OK

**Вихідні дані:**
- `data/canonical/cot_weekly_canonical.parquet`
- `data/canonical/qa_report.txt` (OK або список помилок)

**Схема canonical:**
- `market_key` (str) - ключ ринку (EUR, JPY, GBP, GOLD)
- `contract_code` (str, 6 digits) - CFTC contract code
- `report_date` (date) - дата звіту
- `open_interest_all` (numeric) - загальний open interest
- `comm_long`, `comm_short`, `comm_net` - Commercial позиції
- `noncomm_long`, `noncomm_short`, `noncomm_net` - Non-Commercial позиції
- `nonrept_long`, `nonrept_short`, `nonrept_net` - Nonreportable позиції
- `raw_source_year`, `raw_source_file` - lineage

**Ключові файли:**
- `run_normalize.py` - головна логіка
- `cot_parser.py` - парсинг annual.txt
- `qa_checks.py` - QA перевірки (`run_qa()`)

---

### 3. INDICATORS (`src/indicators/run_indicators.py`)

**Призначення:** Розрахунок індикаторів та торгових сигналів

**Вхідні дані:**
- `data/canonical/cot_weekly_canonical.parquet`

**Процес:**
1. **Indicators calculation:**
   - Мапить Non-Commercial → Funds (для MVP)
   - Розраховує WoW зміни (funds_net_chg, oi_chg) через `groupby().diff()`
   - Нормалізує: funds_net_pct_oi, funds_flow_pct_oi, oi_chg_pct
   - Додає quality flags

2. **Signal generation:**
   - Статуси: ACTIVE або PAUSE (тільки 2 стани)
   - Правила:
     - ACTIVE: |funds_flow_pct_oi| >= 0.5% AND oi_chg >= 0
     - PAUSE: інакше (NO_HISTORY_OR_BAD_OI, FLOW_OK_OI_DOWN, FLOW_SMALL)
   - Reason codes для дебагу

**Вихідні дані:**
- `data/indicators/indicators_weekly.parquet`
- `data/indicators/signal_status.parquet`

**Схема indicators_weekly:**
- `market_key`, `report_date`
- `open_interest`, `funds_long`, `funds_short`, `funds_net`
- `funds_long_chg`, `funds_short_chg`, `funds_net_chg`, `oi_chg`
- `funds_net_pct_oi`, `funds_flow_pct_oi`, `oi_chg_pct`
- Quality flags

**Схема signal_status:**
- `market_key`, `report_date`
- `status` (ACTIVE/PAUSE)
- `reason_code` (FLOW_OK_OI_OK, FLOW_SMALL, etc.)

**Ключові файли:**
- `run_indicators.py` - головна логіка
- `cot_indicators.py` - `build_indicators_weekly()`
- `signal_rules.py` - `build_signal_status()`

---

### 4. REPORT (`src/report/run_report.py`)

**Призначення:** Генерація HTML-звітів

**Вхідні дані:**
- `data/indicators/indicators_weekly.parquet`
- `data/indicators/signal_status.parquet`

**Процес:**
1. Завантажує indicators та signals
2. Визначає report week (max report_date)
3. Для кожного ринку:
   - Отримує ключові метрики (funds_net, funds_net_chg, open_interest, etc.)
   - Отримує статус сигналу (ACTIVE/PAUSE) та reason_code
   - Генерує графік funds_net over time (matplotlib → base64)
4. Рендерить HTML через Jinja2 template

**Вихідні дані:**
- `reports/{report_week}/{report_week}_weekly_cot_report.html`

**Ключові файли:**
- `run_report.py` - головна логіка
- `render.py` - функції рендерингу
- `template.html` - HTML шаблон

---

### 5. ML BACKUP (`src/normalize/run_ml_backup.py`)

**Призначення:** Створення очищеного датасету для ML

**Вхідні дані:**
- `data/canonical/cot_weekly_canonical.parquet`

**Процес:**
1. Читає canonical dataset
2. Вибирає тільки "чисті" колонки (без raw_source_*)
3. Виконує QA перевірки
4. Зберігає у parquet (обов'язково) та CSV (опційно)

**Вихідні дані:**
- `data/ml/cot_weekly_ml.parquet`
- `data/ml/cot_weekly_ml.csv` (якщо `--csv`)

**Ключові файли:**
- `run_ml_backup.py` - головна логіка

---

## ⚙️ Конфігурація

### `configs/markets.yaml`

Конфігурація ринків та джерела даних:

```yaml
source:
  dataset: "legacy_futures_only"
  cftc_historical_zip_url_template: "https://www.cftc.gov/files/dea/history/deacot{year}.zip"

markets:
  - market_key: "EUR"
    contract_code: "099741"
  - market_key: "JPY"
    contract_code: "097741"
  - market_key: "GBP"
    contract_code: "096742"
  - market_key: "GOLD"
    contract_code: "088691"
```

**Важливо:** Новий ринок додається через contract_code (не через назву ринку).

---

## 🚀 Запуск Pipeline

### Послідовність виконання

```bash
# 1. Завантаження даних (перший раз або оновлення)
python -m src.ingest.run_ingest

# 2. Нормалізація
python -m src.normalize.run_normalize

# 3. Розрахунок індикаторів
python -m src.indicators.run_indicators

# 4. Генерація звіту
python -m src.report.run_report

# 5. (Опційно) ML backup
python -m src.normalize.run_ml_backup --csv
```

### Параметри

**Ingest:**
```bash
python -m src.ingest.run_ingest --start-year 2011 --end-year 2025 --log-level INFO
```

**Normalize:**
```bash
python -m src.normalize.run_normalize --root . --log-level INFO
```

**ML Backup:**
```bash
python -m src.normalize.run_ml_backup --csv  # Додає CSV файл
```

---

## 📊 Структура даних

### Canonical Dataset

**Файл:** `data/canonical/cot_weekly_canonical.parquet`

**Гранулярність:** 1 рядок = 1 market_key × 1 report_date

**Колонки:**
- `market_key` (str): EUR, JPY, GBP, GOLD
- `contract_code` (str, 6 digits): CFTC contract code
- `report_date` (date): Дата звіту (вівторок COT тижня)
- `open_interest_all` (numeric): Загальний open interest
- `comm_long`, `comm_short`, `comm_net` (numeric): Commercial позиції
- `noncomm_long`, `noncomm_short`, `noncomm_net` (numeric): Non-Commercial позиції
- `nonrept_long`, `nonrept_short`, `nonrept_net` (numeric): Nonreportable позиції
- `raw_source_year` (int): Рік джерела
- `raw_source_file` (str): Назва файлу джерела

### Indicators Dataset

**Файл:** `data/indicators/indicators_weekly.parquet`

**Гранулярність:** 1 рядок = 1 market_key × 1 report_date

**Ключові колонки:**
- `funds_net`: Net позиція Funds (Non-Commercial)
- `funds_net_chg`: WoW зміна funds_net
- `funds_net_pct_oi`: funds_net / open_interest
- `funds_flow_pct_oi`: funds_net_chg / open_interest
- Quality flags

### Signal Status

**Файл:** `data/indicators/signal_status.parquet`

**Статуси:**
- `ACTIVE`: Сигнал активний (потік >= 0.5% OI, OI не зменшується)
- `PAUSE`: Сигнал на паузі

**Reason codes:**
- `FLOW_OK_OI_OK`: Потік та OI OK
- `FLOW_OK_OI_DOWN`: Потік OK, але OI зменшується
- `FLOW_SMALL`: Потік замалий (< 0.5% OI)
- `NO_HISTORY_OR_BAD_OI`: Немає історії або поганий OI

---

## 🧪 QA та Валідація

### Normalize QA (blocking)

Перевірки в `src/normalize/qa_checks.py`:

1. **Uniqueness:** (market_key, report_date) без дублів
2. **Whitelist integrity:** Тільки дозволені market_key та contract_code
3. **Null ratio:** <= 0.1% для numeric колонок
4. **Open interest:** >= 0

Якщо QA fail → parquet НЕ записується, скрипт падає з помилкою.

### ML Backup QA

Перевірки в `run_ml_backup.py`:

1. **Uniqueness:** (market_key, report_date) без дублів
2. **report_date:** not null
3. **contract_code:** string, 6 символів

---

## 🔧 Залежності

```txt
pandas>=2.2          # Робота з даними
pyarrow>=16.0        # Parquet формат
pyyaml>=6.0          # Конфігурація
jinja2>=3.1          # HTML шаблони
python-dateutil>=2.9 # Парсинг дат
requests>=2.31       # HTTP завантаження
tenacity>=8.2        # Retry логіка
```

**Встановлення:**
```bash
pip install -r requirements.txt
```

---

## 📝 Ключові принципи архітектури

1. **Immutability:** Raw snapshots зберігаються з timestamp, не перезаписуються
2. **Manifest-driven:** Normalize читає список файлів з manifest, не через glob
3. **QA blocking:** Canonical parquet записується тільки після успішних QA
4. **Config-driven markets:** Ринки конфігуруються через contract codes, не hardcode
5. **Deterministic:** Всі розрахунки детерміновані (без look-ahead)
6. **Separation of concerns:** Чітке розділення ingest → normalize → indicators → report

---

## 🎯 Статус проекту

**Поточний стан:**
- ✅ Ingest: Працює, підтримує refresh window
- ✅ Normalize: Працює, з QA перевірками
- ✅ Indicators: Працює, генерація сигналів ACTIVE/PAUSE
- ✅ Report: Працює, HTML звіти з графіками
- ✅ ML Backup: Працює, очищений датасет

**Дані:**
- Період: 2015-01-06 до 2025-12-16
- Ринки: EUR, JPY, GBP, GOLD
- Рядків в canonical: ~2,288 (4 ринки × ~572 тижні)

---

## 📚 Додаткова інформація

### Manifest формат

`data/raw/manifest.csv` містить:
- `dataset`, `year`, `url`
- `downloaded_at_utc`, `raw_path`, `sha256`, `size_bytes`
- `status` (OK, ERROR, UNCHANGED)
- `error` (якщо ERROR)

### Refresh Window

Ingest автоматично оновлює дані для поточного та минулого року. Старіші роки skip, якщо вже є OK snapshot.

### Contract Codes

Кожен ринок ідентифікується через CFTC Contract Market Code (6 цифр). Це гарантує точність, оскільки назви ринків можуть змінюватися.

---

## 🤝 Контрибуція

При додаванні нових ринків:
1. Додати запис у `configs/markets.yaml` з `market_key` та `contract_code`
2. Перезапустити pipeline
3. Перевірити QA

---

**Версія документації:** 1.0  
**Останнє оновлення:** 2025-12-31

