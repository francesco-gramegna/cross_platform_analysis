"""
Integrate 2022 TikTok raw data into merged_2022_all.csv.

What TikTok 2022 has:    rank (some months), handle_tiktok, name_tiktok,
                          followers, views_avg, likes_avg, comments_avg, shares_avg
What it lacks:            audience_country, category  → filled with NaN
engagement_avg derived:   likes_avg + comments_avg  (same logic as YouTube rows)
"""

import os
import numpy as np
import pandas as pd

BASE  = "/Users/draco/Desktop/2026 Spring/DS516/project/cross_platform_analysis"
RAW   = os.path.join(BASE, "crude_dataset", "kaggle_2022")
OUT   = os.path.join(BASE, "cleaned_dataset", "updated")

# ── helper: parse "60.3M" / "30.8K" / "19K" → float ─────────────────────────
def parse_shorthand(s):
    if pd.isna(s):
        return np.nan
    s = str(s).strip().replace(",", "")
    multipliers = {"K": 1e3, "M": 1e6, "B": 1e9}
    for suffix, mult in multipliers.items():
        if s.endswith(suffix):
            try:
                return float(s[:-1]) * mult
            except ValueError:
                return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan

# month-filename → month label used in existing data
MONTH_MAP = {
    "tiktok_december":  "dec",
    "tiktok_june":      "june",
    "tiktok_march":     "mar",
    "tiktok_november":  "nov",
    "tiktok_september": "sep",
}

# ── load & parse all TikTok monthly files ─────────────────────────────────────
tiktok_parts = []
for fname, month_label in MONTH_MAP.items():
    path = os.path.join(RAW, fname)
    df = pd.read_csv(path)

    # parse numeric columns
    for col in ["followers", "views_avg", "likes_avg", "comments_avg", "shares_avg"]:
        if col in df.columns:
            df[col] = df[col].apply(parse_shorthand)

    # rank may be missing in some months
    if "rank" not in df.columns:
        df["rank"] = np.nan

    df["_month"] = month_label
    tiktok_parts.append(df)

tiktok_raw = pd.concat(tiktok_parts, ignore_index=True)
print(f"TikTok rows loaded: {len(tiktok_raw)}")

# ── build rows that match the merged_2022 schema ──────────────────────────────
existing = pd.read_csv(os.path.join(OUT, "merged_2022_all.csv"))
print(f"Existing merged rows: {len(existing)}")

tiktok_rows = pd.DataFrame({
    "rank":             tiktok_raw["rank"],
    "handle_instagram": np.nan,
    "name_instagram":   np.nan,
    "category_1":       np.nan,
    "category_2":       np.nan,
    "followers":        tiktok_raw["followers"],
    "audience_country": np.nan,          # not available in 2022 TikTok data
    "engagement_auth":  np.nan,
    # engagement_avg = likes + comments  (mirrors YouTube rows in existing data)
    "engagement_avg":   tiktok_raw["likes_avg"] + tiktok_raw["comments_avg"],
    "category_primary": np.nan,
    "category_unified": np.nan,          # no category info in 2022 TikTok
    "subcategory":      np.nan,
    "_platform":        "TikTok",
    "_month":           tiktok_raw["_month"],
    "_year":            2022,
    "handle_youtube":   np.nan,
    "name_youtube":     np.nan,
    "views_avg":        tiktok_raw["views_avg"],
    "likes_avg":        tiktok_raw["likes_avg"],
    "comments_avg":     tiktok_raw["comments_avg"],
    # TikTok-specific — new column, NaN for all non-TikTok rows
    "handle_tiktok":    tiktok_raw["handle_tiktok"],
    "name_tiktok":      tiktok_raw["name_tiktok"],
    "shares_avg":       tiktok_raw["shares_avg"],
})

# add the new TikTok-only columns to the existing data (fill with NaN)
for col in ["handle_tiktok", "name_tiktok", "shares_avg"]:
    existing[col] = np.nan

merged = pd.concat([existing, tiktok_rows], ignore_index=True)
print(f"Merged rows after adding TikTok: {len(merged)}")
print("Platform counts:\n", merged["_platform"].value_counts().to_string())

# ── save ──────────────────────────────────────────────────────────────────────
out_path = os.path.join(OUT, "merged_2022_all.csv")
merged.to_csv(out_path, index=False)
print(f"\n✅  Saved → {out_path}")

# quick sanity check
print("\nSample TikTok rows:")
print(
    merged[merged["_platform"] == "TikTok"]
    [["rank","handle_tiktok","name_tiktok","followers","engagement_avg",
      "views_avg","likes_avg","comments_avg","shares_avg","_month"]]
    .head(5)
    .to_string()
)
