# Cleaning Log — Step 4: ER Calculation

**Script:** `4 - ER calculation/scripts/4_er_calculation.py`
**Input:**  `3 - handles merging/finalData.csv`
**Output:** `4 - ER calculation/finalData_with_er.csv`

---

## Column Renames (match raw-source semantics)

The two IG 2022 columns had misleading names — neither was a percentage.
Both held **counts** (values up to ~17M), differing only in whether bot-filtering
was applied upstream.

| Old name          | New name          | What it actually is                      |
|-------------------|-------------------|------------------------------------------|
| `engagement_rate` | `engagement_auth` | Authentic engagement count (bot-filtered)|
| `engagement_avg`  | `engagement_total`| Total engagement count (unfiltered)      |

---

## New Columns

### `engagement_count` — unified engagement count
Coalesced by source, in this order:

1. **Instagram 2022** → `engagement_total` (the unfiltered count from raw)
2. **Any 2024 row** (all platforms) → reconstructed as `er% × followers`
3. **TikTok 2022 / YouTube 2022 / YouTube 2026** → `likes_avg + comments_avg + views_avg + shares_avg` (NaN treated as 0 inside the sum; row stays NaN only if *all four* are missing)

### `er_pct` — engagement rate as a percentage
`er_pct = engagement_count / followers * 100`, computed from the unified count
so every row is on the same formula. Rows with NaN or zero followers → NaN.

---

## Coverage of New Columns

| Slice | non-null % |
|---|---|
| Instagram 2022 | 99.7% |
| Instagram 2024 | 98.9% |
| TikTok 2022    | 100.0% |
| TikTok 2024    | 25.8% |
| YouTube 2022   | 100.0% |
| YouTube 2024   | 38.5% |
| YouTube 2026   | 54.8% |

Gaps in 2024 TT/YT and 2026 YT reflect missing raw metrics (HypeAuditor `er="-"`
or failed 2026 re-scrapes), not a computation issue.

### Sanity Check
For the 9,431 rows in 2024 where raw `er` exists, reconstructed `er_pct` matches
`er` to within floating-point error (mean |diff| = 6.1e-17).

---

## ⚠️ Caveat — Definitions Are Not Identical Across Sources

Because `views_avg` and `shares_avg` were included for TT 2022 / YT 2022 / YT 2026
per the project decision, `er_pct` does **not** have the same definition in every row:

| Source | Numerator |
|---|---|
| IG 2022 | likes + comments (from raw `engagement_avg`) |
| All 2024 | likes + comments only (HypeAuditor convention) |
| TT 2022, YT 2022, YT 2026 | likes + comments + **views** + **shares** |

Because TikTok views frequently exceed follower counts (viral content), TikTok 2022
`er_pct` runs an order of magnitude higher than the other slices (median 70% vs
~1–3% elsewhere). Treat cross-platform comparisons of raw `er_pct` with caution:

- **Within-platform trends** (e.g., YT 2022 vs YT 2026 panel) remain valid — definition is consistent inside each slice.
- **Cross-platform comparisons** should note the definitional difference, or be re-run on a "likes + comments only" variant if strict comparability is needed.
