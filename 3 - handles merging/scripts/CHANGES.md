## Cleaning Log — Step 3: Handles Merging / Preprocessing

**Script:** `3 - handles merging/merge_all_data.py`  
**Input:** `2 - countries and numbers fixed/`  
**Output:** `3 - handles merging/preprocessedData.csv`  

---

## 2022

### Handle & Name Unification
- `handle_instagram`, `handle_tiktok`, `handle_youtube` → `handle`
- `name_instagram`, `name_tiktok`, `name_youtube` → `name`

### Deduplication
We deduplicate some accounts that have beens scraped multiple times in the same snapshot
- Key: (`handle`, `_month`, `_year`, `_platform`)
- Priority:
  - `category_unified` present
  - higher `followers`
- Removed: `rank`

---

## 2024

### Handle Extraction
- Parsed `handle` from `name` (split on `@`)

### Global Deduplication
- Dropped `_is_global = False` rows if same `handle` exists in global
- Removed: `rank`

---

## 2026

### Column Cleanup
- Removed: `status`, `error`, `processed_at_unix`
- `handle_youtube` → `handle`
- `name_youtube` → `name`

---

## Cross-Year

### Column Standardization
- Renamed:
  - `avg_likes` → `likes_avg`
  - `avg_views` → `views_avg`
  - `avg_comments` → `comments_avg`

### Output
- Unified schema across all years
- Columns ordered with priority:
  - `handle`, `name`, `_platform`, `_year`, `_month`, `category_unified`

---

**Script:** `3 - handles merging/populate_script.py`  
**Input:** `3 - handles merging/preprocessedData.csv`  
**Output:** `3 - handles merging/finalData.csv`  

We merge the similar accounts based on a hierarchical clustering with custom rules.
We then populate the 'populated\_category' using the 'category\_unified' and the leading category in each cluster of accounts.




