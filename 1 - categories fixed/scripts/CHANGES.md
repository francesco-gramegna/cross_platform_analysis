# Cleaning Log

---

## Step 1 — Categories Fixed (2022)

**Script:** `1 - categories fixed/scripts/1_categories_2022.py`  
**Input:** `crude_dataset/kaggle_2022/`  
**Output:** `1 - categories fixed/2022/`  

### What Was Fixed

#### 1. Column Name Typos
- `instagram_september`: `' name_instagram'` (leading space) → `name_instagram`
- `tiktok_december`: `'fo llowers'` (internal space) → `followers`

#### 2. Missing Rank Column
Files with no `rank` column had it added as a sequential integer (1 to n) based on row order:
- `instagram_june`
- `tiktok_june`
- `tiktok_march`
- `youtube_june`
- `youtube_march`
- `youtube_september`

#### 3. instagram_june Mislabeled Schema
Column names were shifted in the raw file. Corrected as follows:

| Wrong name | Correct name |
|---|---|
| `views_avg` | `audience_country` |
| `likes_avg` | `engagement_auth` |
| `comments_avg` | `engagement_avg` |

#### 4. Category Mapping (Instagram & YouTube only)
- `category_1` values mapped to `category_unified` using a 7-class scheme:
  `Entertainment`, `Music`, `Sports`, `Beauty&Fashion`, `Tech&Gaming`, `Knowledge&Info`, `Lifestyle`, `Other`
- New column `category_status` added per row: `MAPPED`, `NA`, or `UNMAPPED`
- Unmapped values are preserved in `category_1` and flagged — they are not dropped
- TikTok skipped — no category column exists in 2022 data (confirmed from raw files)
- No unmapped categories found — map covers all raw values in 2022 data
- See `mapping_report_2022.csv` for per-file mapped/NA counts

### Verified Output
- 15 individual cleaned files saved with `.csv` extension
- `merged_2022_all.csv`: 15,150 rows × 23 columns
  - instagram: 5,072 rows
  - youtube: 5,071 rows
  - tiktok: 5,007 rows
- Months: september (3,097), june (3,050), december (3,003), march (3,000), november (3,000)

### Deferred Issues (not fixed in this step)
- `category_status` shows `NaN` instead of `"NA"` for rows where `category_1` was originally missing
- Country column name inconsistency (`country` vs `audience_country` across YouTube files)
- Numeric columns still stored as strings with M/K suffixes

---

## Step 2 — Categories Fixed (2024)

**Scripts:** `1 - categories fixed/scripts/1_categories_2024.py`, `translate_and_remap_2024.py`  
**Input:** `crude_dataset/2024/`  
**Output:** `1 - categories fixed/2024/`  

### What Was Fixed

#### 1. Column Names Standardized
All columns renamed to lowercase with underscores: `#` → `rank`, `NAME` → `name`, `TOPIC OF INFLUENCE` → `topic_of_influence`, etc.

#### 2. Foreign Language Column Headers (11 files)
11 files were scraped with a non-English UI, producing foreign-language column names and extra columns (`save`, `invite to campaign`). Fixed by remapping columns by position and truncating to the standard 7 columns:

| File | Language detected |
|---|---|
| `tiktok_belgium` | German |
| `instagram_brazil` | Persian |
| `youtube_czechia` | Persian/Urdu |
| `youtube_finland` | Chinese |
| `tiktok_indonesia` | Bulgarian |
| `youtube_morocco` | Arabic |
| `tiktok_poland` | Croatian |
| `instagram_romania` | Arabic |
| `tiktok_sweden` | Swedish |
| `instagram_united-arab-emirates` | Portuguese |
| `youtube_united-kingdom` | Spanish |

#### 3. Row Tagging
Each row tagged with `_platform`, `_country`, `_is_global`, `_year=2024`.

#### 4. Threads Platform Excluded
Threads data is present in the raw dataset but excluded from this analysis. Files exist for all countries except `aland-islands`.

#### 5. Category Mapping
- `TOPIC OF INFLUENCE` (free text) mapped to `category_unified` using keyword rules
- Same 7 categories as 2022 for cross-year comparability
- Priority-ordered keyword matching: specific categories first, broad ones last
- New column `category_status` added: `MAPPED`, `NA`, or `UNMAPPED`
- Keywords added beyond original rules: `ice hockey`, `exercise`, `shopping`, `product presentation`, `product presentations`, `careers`, `quotes`, `guns`, `policy`, `rap`, `movies`, `famous`, `fame`, `mothers`, `trip`, `trips`, `travels`, `photo`, `children`, `video blogger`
- Plurals added for existing keywords: `movie` → also `movies`, `career` → also `careers`

#### 6. Foreign Language Topic Translation
11 affected files had topic content in foreign languages. Translated via Google Translate (`deep-translator`, no API key). Translation lookup table saved to `topic_translations_2024.csv`.
- Additional Estonian strings in `instagram_united-kingdom` not caught in initial pass — corrected manually
- One mistranslation found: Portuguese `"Arte"` → `"until"` — corrected to `"Art"`
- One mistranslation: Estonian `"Modellindus"` → `"Model bird"` — corrected to `"Modeling"`

**Methodology note:** "Non-English topic fields translated via Google Translate (deep-translator) prior to category mapping. Mistranslations identified during unmapped review were corrected manually."

### Verified Output
- 59 country folders × 3 platforms = 177 individual cleaned files
- Merged files:
  - `merged_2024_instagram.csv`: 6,013 rows — mapped: 5,511, NA: 502, unmapped: 0
  - `merged_2024_tiktok.csv`: 6,035 rows — mapped: 2,476, NA: 3,556, unmapped: 0
  - `merged_2024_youtube.csv`: 6,020 rows — mapped: 421, NA: 5,599, unmapped: 0
- High NA rates on TikTok (59%) and YouTube (93%) reflect platform data availability, not cleaning errors

### Deferred Issues (not fixed in this step)
- Numeric columns still stored as strings with M/K suffixes
- `ER` column contains `"-"` for missing values instead of `NaN`
- Country column name standardization

---

## Step 3 — Categories Fixed (2026)

**Script:** `1 - categories fixed/scripts/1_categories_2026.py`  
**Input:** `crude_dataset/2026/2026`  
**Output:** `1 - categories fixed/2026/2026_youtube.csv`  

### Notes on 2026 Data
- YouTube only — no Instagram or TikTok
- Numeric columns already clean (no M/K suffixes)
- Country is 2-letter ISO code — standardization deferred

### What Was Fixed

#### 1. Category Mapping
- `category` (Wikipedia-style labels) mapped to `category_unified` using a direct dictionary lookup
- Same 7 categories as 2022 and 2024 for cross-year comparability
- 0 unmapped categories found
- New column `category_status` added: `MAPPED` or `NA`

#### 2. Row Tagging
- Each row tagged with `_platform = 'youtube'`, `_year = 2026`
- File saved as `2026_youtube.csv`

### Verified Output
- `2026_youtube.csv`: 998 rows
  - Mapped: 573 (57.4%)
  - NA: 425 (42.6%)
  - Unmapped: 0

### Deferred Issues (not fixed in this step)
- 425 rows with `category_status = NA` correspond to channels where the scraper failed (`exists = 0`, `status = error`). These rows have no usable data. **Flag for dropping in a later cleaning step.**
- Country column uses 2-letter ISO codes instead of full names — standardization deferred
- Numeric columns not yet standardized across years (already clean in 2026 but not in 2022)
