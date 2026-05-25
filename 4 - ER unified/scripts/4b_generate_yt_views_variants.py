"""
Step 4b: Generate the two YouTube ER variants side-by-side.

Writes:
  - finalData_with_er_yt_no_views.csv      (YT engagement_count = likes + comments only)
  - finalData_with_er_yt_with_views.csv    (YT engagement_count = likes + comments + views)

Everything else (Instagram 2022, TikTok 2022, all 2024 slices) is identical
across the two outputs. Only the YouTube engagement_count and er_pct columns
differ. This produces clearly-labeled BEFORE/AFTER snapshots for the YT-views
decision.
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC  = ROOT / "3 - handles merging" / "finalData.csv"
OUT_DIR = ROOT / "4 - ER unified"
OUT_DIR.mkdir(exist_ok=True)

df_base = pd.read_csv(SRC, low_memory=False)
print(f"Loaded {len(df_base):,} rows from {SRC.name}")

# --- Rename misleading columns (shared by both variants) -----------------
df_base = df_base.rename(columns={
    "engagement_rate": "engagement_auth",
    "engagement_avg":  "engagement_total",
})

def build(df, yt_include_views: bool):
    """Compute engagement_count and er_pct for one variant."""
    df = df.copy()
    is_ig22 = (df["_platform"] == "instagram") & (df["_year"] == 2022)
    is_2024 = (df["_year"] == 2024)
    is_yt   = (df["_platform"] == "youtube")
    is_tt   = (df["_platform"] == "tiktok")

    yt_components = (["likes_avg", "comments_avg", "views_avg"] if yt_include_views
                     else ["likes_avg", "comments_avg"])
    yt_sum     = df[yt_components].fillna(0).sum(axis=1)
    yt_has_any = df[yt_components].notna().any(axis=1)

    tt_components = ["likes_avg", "comments_avg", "shares_avg"]
    tt_sum     = df[tt_components].fillna(0).sum(axis=1)
    tt_has_any = df[tt_components].notna().any(axis=1)

    engagement_count = pd.Series(np.nan, index=df.index, dtype="float64")
    engagement_count.loc[is_ig22] = df.loc[is_ig22, "engagement_total"]
    engagement_count.loc[is_2024 & df["er"].notna() & df["followers"].notna()] = (
        df.loc[is_2024, "er"] / 100.0 * df.loc[is_2024, "followers"]
    )
    yt_fill = engagement_count.isna() & is_yt & yt_has_any
    engagement_count.loc[yt_fill] = yt_sum.loc[yt_fill]
    tt_fill = engagement_count.isna() & is_tt & tt_has_any
    engagement_count.loc[tt_fill] = tt_sum.loc[tt_fill]
    df["engagement_count"] = engagement_count

    df["er_pct"] = np.where(
        df["followers"].notna() & (df["followers"] > 0) & df["engagement_count"].notna(),
        df["engagement_count"] / df["followers"] * 100.0, np.nan,
    )
    return df

variants = {
    "yt_no_views":   {"yt_include_views": False,
                       "out": OUT_DIR / "finalData_with_er_yt_no_views.csv",
                       "label": "BEFORE — YT engagement = likes + comments (no views)"},
    "yt_with_views": {"yt_include_views": True,
                       "out": OUT_DIR / "finalData_with_er_yt_with_views.csv",
                       "label": "AFTER  — YT engagement = likes + comments + views"},
}

for name, cfg in variants.items():
    df = build(df_base, cfg["yt_include_views"])
    df.to_csv(cfg["out"], index=False)
    yt_med_22 = df[(df["_platform"] == "youtube") & (df["_year"] == 2022)]["er_pct"].median()
    yt_med_26 = df[(df["_platform"] == "youtube") & (df["_year"] == 2026)]["er_pct"].median()
    print(f"\n{cfg['label']}")
    print(f"  → {cfg['out'].name}")
    print(f"  YT 2022 median er_pct: {yt_med_22:.4f}%")
    print(f"  YT 2026 median er_pct: {yt_med_26:.4f}%")

print("\nDone. Both variants saved in 4 - ER unified/.")
