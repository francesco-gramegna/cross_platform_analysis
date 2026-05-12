"""
Step 4: Engagement rate unification

Input:  3 - handles merging/finalData.csv
Output: 4 - ER calculation/finalData_with_er.csv

Builds a single `engagement_count` and `er_pct` column across all sources.
"""

from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC  = ROOT / "3 - handles merging" / "finalData.csv"
OUT_DIR = ROOT / "4 - ER unified"
OUT_DIR.mkdir(exist_ok=True)
OUT = OUT_DIR / "finalData_with_er.csv"

df = pd.read_csv(SRC, low_memory=False)
print(f"Loaded {len(df):,} rows from {SRC.name}")

# --- 1. Rename misleading columns to match raw source names -----------------
df = df.rename(columns={
    "engagement_rate": "engagement_auth",   # raw: engagement_auth (authentic count)
    "engagement_avg":  "engagement_total",  # raw: engagement_avg  (total count)
})

# --- 2. Build unified engagement_count --------------------------------------
# Definition: engagement_count counts INTERACTIONS only (likes + comments + shares).
# Views are excluded — they are passive exposure, not engagement, and the
# industry-standard ER formula (HypeAuditor, Hootsuite, Sprout Social, etc.)
# excludes them.
#
# Priority by source:
#   IG 2022              : use engagement_total (HypeAuditor interactions aggregate, views-free)
#   Any 2024 row         : reconstruct from er% × followers (source `er` is interactions-based)
#   TT/YT 2022, YT 2026  : sum of likes + comments + shares (NaN→0); VIEWS EXCLUDED
is_ig22 = (df["_platform"] == "instagram") & (df["_year"] == 2022)
is_2024 = (df["_year"] == 2024)

interaction_cols = ["likes_avg", "comments_avg", "shares_avg"]
sum_cols = df[interaction_cols].fillna(0).sum(axis=1)
has_any_count = df[interaction_cols].notna().any(axis=1)

engagement_count = pd.Series(np.nan, index=df.index, dtype="float64")
engagement_count.loc[is_ig22] = df.loc[is_ig22, "engagement_total"]
engagement_count.loc[is_2024 & df["er"].notna() & df["followers"].notna()] = (
    df.loc[is_2024, "er"] / 100.0 * df.loc[is_2024, "followers"]
)
fill_mask = engagement_count.isna() & has_any_count
engagement_count.loc[fill_mask] = sum_cols.loc[fill_mask]

df["engagement_count"] = engagement_count

# --- 3. Compute er_pct consistently from engagement_count / followers -------
df["er_pct"] = np.where(
    df["followers"].notna() & (df["followers"] > 0) & df["engagement_count"].notna(),
    df["engagement_count"] / df["followers"] * 100.0,
    np.nan,
)

# --- 4. Save ----------------------------------------------------------------
df.to_csv(OUT, index=False)
print(f"Wrote {OUT}")

# --- 5. Report --------------------------------------------------------------
print("\n=== Coverage of new columns by platform × year ===")
for col in ["engagement_count", "er_pct"]:
    print(f"\n{col} — non-null % by platform × year:")
    cov = df.groupby(["_platform", "_year"])[col].apply(
        lambda s: (s.notna().mean() * 100).round(1)
    )
    print(cov.to_string())

print("\n=== er_pct distribution (overall, non-null) ===")
print(df["er_pct"].describe().round(3).to_string())

print("\n=== Sanity check: reconstructed er_pct vs raw `er` on 2024 rows ===")
m = (df["_year"] == 2024) & df["er"].notna() & df["er_pct"].notna()
if m.sum():
    diff = (df.loc[m, "er_pct"] - df.loc[m, "er"]).abs()
    print(f"rows checked: {m.sum():,} | mean |diff|: {diff.mean():.4g} | max: {diff.max():.4g}")
