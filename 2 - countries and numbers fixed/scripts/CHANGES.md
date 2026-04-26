# Cleaning Log — Step 2: Countries and Numbers

**Script:** `2 - countries and numbers fixed/scripts/2_countries_and_numbers.py`  
**Input:** `1 - categories fixed/`  
**Output:** `2 - countries and numbers fixed/`  

---

## 2022

### Country Column
- `country` and `audience_country` coalesced into a single `audience_country` column
- Both columns contained audience country data (verified via T-Series and PewDiePie) — the name difference was a scraping inconsistency across months, not a semantic difference
- `"-"` replaced with `NaN`
- `country` column dropped after coalescing
- TikTok has no country data — `audience_country` is `NaN` for all TikTok rows

### Numeric Columns Converted (string with M/K suffixes → float)
| Platform | Columns converted |
|---|---|
| Instagram | `followers`, `engagement_auth`, `engagement_avg` |
| TikTok | `followers`, `views_avg`, `likes_avg`, `comments_avg`, `shares_avg` |
| YouTube | `followers`, `views_avg`, `likes_avg`, `comments_avg` |

### Verified Output
- `merged_2022_all.csv`: 15,150 rows
- `audience_country` filled: instagram 5,049, youtube 4,199, tiktok 0

---

## 2024

### Country Column
- `country` renamed to `audience_country` for consistency across years

### Numeric Columns Converted
- `followers` → float (M/K suffixes removed)
- `potential_reach` → float (M/K suffixes removed)
- `er` → float (% sign stripped, `"-"` → `NaN`)

### Verified Output
- `merged_2024_instagram.csv`: 6,013 rows
- `merged_2024_tiktok.csv`: 6,035 rows
- `merged_2024_youtube.csv`: 6,020 rows

---

## 2026

### Country Column
- 2-letter ISO codes converted to full country names via lookup table
- `country` renamed to `audience_country`
- 42 unique ISO codes mapped

### Numeric Columns
- Already clean — no conversion needed

### Verified Output
- `2026_youtube.csv`: 998 rows
  - `audience_country` filled: 507
  - `audience_country` NA: 491

---

## Deferred Issues

- **2026 failed scrape rows:** 491 rows with `exists = 0`, `status = error`, and no usable data (no category, no country, no metrics). These were flagged in Step 1 and remain in the dataset. **Flag for dropping in a later cleaning step.**
- **2026 failed scrape rows:**
- `category_status = NaN` (instead of `"NA"`) for rows where `category_1` was originally missing in 2022 — flagged in Step 1, still present.