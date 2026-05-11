# Cleaning Log — Step 4: ER Calculation

**Script:** `4 - ER unified/scripts/4_er_calculation.py`
**Input:**  `3 - handles merging/finalData.csv`
**Output:** `4 - ER unified/finalData_with_er.csv`

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

### `engagement_count` — unified **interactions** count
Engagement is defined here as **active interactions only**: likes + comments + shares.
Views are excluded by design (see correction note below).

Coalesced by source, in this order:

1. **Instagram 2022** → `engagement_total` (HypeAuditor interactions aggregate; views-free)
2. **Any 2024 row** (all platforms) → reconstructed as `er% × followers` (the source `er` field is interactions-based)
3. **TikTok 2022 / YouTube 2022 / YouTube 2026** → `likes_avg + comments_avg + shares_avg` (NaN treated as 0 inside the sum; row stays NaN only if *all three* interaction columns are missing). YouTube 2022 and YouTube 2026 carry no `shares_avg`, so for those slices the sum reduces to `likes_avg + comments_avg`.

### `er_pct` — engagement rate as a percentage
`er_pct = engagement_count / followers * 100`, computed from the unified count
so every row is on the same formula. Rows with NaN or zero followers → NaN.

---

## ⚠️ Correction: Views Excluded from Engagement (2026-04-26)

An earlier version of this step summed `likes + comments + views + shares` for
TT 2022 / YT 2022 / YT 2026. That version was **wrong**: views measure passive
exposure (auto-play, scroll-by impressions), not active engagement, and the
industry-standard definition of engagement rate excludes them
(HypeAuditor, Hootsuite, Sprout Social, Influencer Marketing Hub, and the
marketing literature all use interactions / followers).

Including views also made the pipeline internally inconsistent: IG 2022 and all
2024 rows were already interaction-based, while the three sum-based slices
were not. A component-share analysis (P8 in Step 5 EDA) showed views accounted
for 88–98% of `engagement_count` on those slices, which inflated TikTok 2022's
median `er_pct` to ~70% — an order of magnitude above every other slice. That
artefact disappears once views are dropped.

**Fix applied:** `engagement_count` for the sum-based slices is now
`likes_avg + comments_avg + shares_avg` (views removed). The `views_avg`
column is retained in the CSV as a separate field for downstream use
(e.g., view-rate analyses, reach controls in regressions), but it no longer
contributes to `er_pct`.

---

## Coverage of New Columns

| Slice | non-null % |
|---|---|
| Instagram 2022 | 99.7% |
| Instagram 2024 | 98.9% |
| TikTok 2022    | 100.0% |
| TikTok 2024    | 25.8% |
| YouTube 2022   | 98.8% |
| YouTube 2024   | 38.5% |
| YouTube 2026   | 54.6% |

Gaps in 2024 TT/YT and 2026 YT reflect missing raw metrics (HypeAuditor `er="-"`
or failed 2026 re-scrapes), not a computation issue. YT 2022 and YT 2026
coverage dropped slightly versus the previous (views-included) version because
a handful of rows now have all-NaN interactions despite having a view count.

### Sanity Check
For the 9,431 rows in 2024 where raw `er` exists, reconstructed `er_pct` matches
`er` to within floating-point error (mean |diff| = 6.1e-17).
