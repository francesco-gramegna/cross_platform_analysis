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

### `engagement_count` — platform-specific engagement aggregate

Engagement is defined **platform-by-platform**, reflecting different interaction
mechanics. Views are included for YouTube but not for TikTok or Instagram.

Coalesced by source/platform, in this order:

1. **Instagram 2022** → `engagement_total` (HypeAuditor's pre-aggregated interactions count; views-free by design of the source field)
2. **Any 2024 row** (all platforms) → reconstructed as `er% × followers`. The 2024 source ships only the aggregate `er` field, so engagement composition cannot be adjusted at this step.
3. **YouTube 2022 / 2026** → `likes_avg + comments_avg + views_avg`. **Views are included** because YouTube viewing requires a deliberate click on a thumbnail (active consumption), unlike autoplay-driven platforms.
4. **TikTok 2022** → `likes_avg + comments_avg + shares_avg`. **Views excluded** because the For-You Page autoplays content — views are passive impressions, not active engagement.

NaN values inside the sum are treated as 0; a row stays NaN only if *all* relevant components are missing.

### `er_pct` — engagement rate as a percentage
`er_pct = engagement_count / followers * 100`, computed from the unified count
so every row is on the same formula. Rows with NaN or zero followers → NaN.

---

## ⚠️ Update: Platform-Specific Treatment of Views (2026-05-20)

The current step uses **platform-specific definitions** of `engagement_count`:
YouTube includes `views_avg`; TikTok and Instagram do not. The rationale is
that interaction mechanics differ across platforms:

- **YouTube viewing is deliberate**: viewers click a thumbnail in a feed,
  search result, or recommendation. A view is closer to active consumption
  than to passive scroll-by exposure. Treating it as part of engagement
  reflects this distinct mechanic.
- **TikTok viewing is autoplay-driven**: the For-You Page automatically plays
  the next video and views accumulate from sub-second scroll-by impressions.
  Views on TikTok are therefore passive exposure and remain excluded.
- **Instagram 2022** continues to use HypeAuditor's pre-aggregated
  `engagement_total` field, which is interaction-only by design.

### History of this decision

A prior version of this script (2026-04-26) summed
`likes + comments + views + shares` for all sum-based slices and was flagged
as treating views as engagement universally. We then corrected the script to
exclude views for all three sum-based slices (TT 2022, YT 2022, YT 2026).
On 2026-05-20, after further discussion of the platform-specific mechanics
above, the YouTube portion was revised once more to re-include `views_avg`.
TikTok remains views-excluded.

### Methodological consequences

- `engagement_count` and `er_pct` are **no longer defined identically across
  platforms**. Within-platform comparisons remain consistent; cross-platform
  comparisons of absolute ER magnitudes should be read as ordinal only and
  reported with this caveat.
- After the revision, `views_avg` contributes the dominant share of
  `engagement_count` on YouTube slices (typically 95%+, see Step 5 EDA
  decomposition). This is intentional under the current definition.
- The 2024 slices are unaffected (no per-component columns in the source).

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
