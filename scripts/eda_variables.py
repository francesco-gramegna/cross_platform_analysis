"""
eda_final.py
------------
EDA visualizations using the final cleaned dataset from cleaned_dataset/updated/

CLEANING SECTION (for methodology):
  C1. NA and Unmapped rates by platform/year (TikTok 2022 excluded)
  C2. Mapping source breakdown 2024

EDA SECTION:
  E1. Cross-platform category distribution — 2022 only (IG + YT)
  E2. Cross-year category distribution — Instagram (2022, 2024)
  E3. Cross-year category distribution — TikTok (2024)
  E4. Cross-year category distribution — YouTube (2022, 2024, 2026)
  E5. Top 10 countries — per platform per year (2024: top 100 by followers)
  E6. Country coverage per platform per year
  E7. Follower distribution — per platform, all years (log scale)
  E8. ER box plots — 2024, top 100 by followers per platform

Notes:
  - Category figures: deduplicated by handle within each platform-year
  - Country figures (2024): top 100 by followers per platform
  - 2022 deduplication: keep first occurrence per handle per platform

Output: EDA/figures/
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path

# ============================================================
# 0. SETUP
# ============================================================
BASE    = Path(".")
UPDATED = BASE / "cleaned_dataset" / "updated"
TRANS   = BASE / "1 - categories fixed" / "2024" / "topic_translations_2024.csv"
OUT     = BASE / "EDA" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

CATS = ["Entertainment", "Music", "Sports", "Beauty&Fashion",
        "Tech&Gaming", "Knowledge&Info", "Lifestyle"]

PLATFORM_COLORS = {
    "Instagram": "#E1306C",
    "TikTok":    "#2C2C2C",
    "YouTube":   "#FF0000",
}
YEAR_COLORS = {2022: "#4361EE", 2024: "#F77F00", 2026: "#2DC653"}

plt.rcParams.update({
    "font.family":       "DejaVu Sans",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.alpha":        0.25,
    "grid.linewidth":    0.5,
    "figure.dpi":        150,
})

# ============================================================
# 1. LOAD DATA
# ============================================================
df22 = pd.read_csv(UPDATED / "merged_2022_all.csv", encoding="utf-16")
df24 = pd.read_csv(UPDATED / "merged_2024_all.csv", encoding="utf-16", on_bad_lines="skip")
df26 = pd.read_csv(UPDATED / "merged_2026.csv",     encoding="utf-16")

# Convert followers to float
for df in [df22, df24, df26]:
    df["followers"] = pd.to_numeric(df["followers"], errors="coerce")

# Deduplicate by handle within platform-year (keep highest followers)
def dedup(df):
    return (df.sort_values("followers", ascending=False)
              .drop_duplicates(subset=["platform", "handle"], keep="first")
              .reset_index(drop=True))

df22 = dedup(df22)
df24 = dedup(df24)
df26 = dedup(df26)

# Top 100 per platform by followers (for country figures)
top100_2024 = (df24.sort_values("followers", ascending=False)
                   .groupby("platform")
                   .head(100)
                   .reset_index(drop=True))

print("After dedup:")
for label, df in [("2022", df22), ("2024", df24), ("2026", df26)]:
    print(f"  {label}: {len(df)} rows, platforms: {df['platform'].value_counts().to_dict()}")

# Load translation map for C2
trans_map = {}
if TRANS.exists():
    t = pd.read_csv(TRANS)
    trans_map = {k: v for k, v in zip(t["original"], t["english"])
                 if pd.notna(v) and str(k).strip().lower() != str(v).strip().lower()}

# ============================================================
# HELPER: annotate dominant bar
# ============================================================
def annotate_dominant(ax, bars, vals):
    max_idx = int(np.argmax(vals))
    bar = list(bars)[max_idx]
    ax.annotate("★",
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 4), textcoords="offset points",
                ha="center", fontsize=12, color="black")

# ============================================================
# C1. NA / Unmapped rates
# ============================================================
status_rows = []
configs = [
    (df22, "Instagram", 2022), (df22, "YouTube", 2022),
    (df24, "Instagram", 2024), (df24, "TikTok", 2024), (df24, "YouTube", 2024),
    (df26, "YouTube", 2026),
]
for df, platform, year in configs:
    sub   = df[df["platform"] == platform]
    total = len(sub)
    if total == 0:
        continue
    n_na       = sub["category_unified"].isna().sum()
    n_unmapped = sub["category_unified"].eq("UNMAPPED").sum()
    status_rows.append({"label": f"{platform}\n{year}", "NA": n_na / total * 100,
                        "UNMAPPED": n_unmapped / total * 100})

status_df  = pd.DataFrame(status_rows).set_index("label")

fig, ax = plt.subplots(figsize=(13, 5))
status_df[["NA", "UNMAPPED"]].plot(kind="bar", ax=ax,
    color=["#E74C3C", "#F77F00"], edgecolor="white", alpha=0.85, width=0.7)
ax.set_title("NA and Unmapped Category Rates by Platform and Year\n"
             "(TikTok 2022 excluded — no category data)", fontweight="bold")
ax.set_xlabel("")
ax.set_ylabel("% of all rows")
ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
ax.legend(title="Status")
plt.tight_layout()
plt.savefig(OUT / "C1_na_unmapped_rates.png", bbox_inches="tight")
plt.close()
print("✅ C1 saved")

# ============================================================
# C2. Mapping source breakdown 2024
# ============================================================
map_rows = []
for platform in ["Instagram", "TikTok", "YouTube"]:
    sub   = df24[df24["platform"] == platform]
    total = len(sub)
    n_na       = sub["category_unified"].isna().sum()
    n_unmapped = sub["category_unified"].eq("UNMAPPED").sum()
    mapped     = sub[sub["category_unified"].notna() & ~sub["category_unified"].eq("UNMAPPED")]

    if "topic_of_influence" in sub.columns:
        n_translated = mapped["topic_of_influence"].isin(trans_map.keys()).sum()
        n_direct     = len(mapped) - n_translated
    else:
        n_direct     = len(mapped)
        n_translated = 0

    map_rows.append({
        "platform":               platform,
        "Direct mapping":         n_direct     / total * 100,
        "Mapped via translation": n_translated / total * 100,
        "Unmapped":               n_unmapped   / total * 100,
        "NA (no data)":           n_na         / total * 100,
    })

map_df = pd.DataFrame(map_rows).set_index("platform")
fig, ax = plt.subplots(figsize=(10, 5))
map_df.plot(kind="bar", ax=ax, stacked=True,
            color=["#2DC653", "#4361EE", "#F77F00", "#E74C3C"],
            edgecolor="white", alpha=0.9, width=0.5)
ax.set_title("Category Mapping Source Breakdown — 2024 (% of all rows)", fontweight="bold")
ax.set_xlabel("")
ax.set_ylabel("% of rows")
ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
ax.legend(title="Source", bbox_to_anchor=(1.01, 1), loc="upper left")
plt.tight_layout()
plt.savefig(OUT / "C2_mapping_source_2024.png", bbox_inches="tight")
plt.close()
print("✅ C2 saved")

# ============================================================
# E1. Cross-platform — IG + YT, 2022 only
# ============================================================
platforms_e1 = ["Instagram", "YouTube"]
all_vals_e1  = []
for platform in platforms_e1:
    sub   = df22[(df22["platform"] == platform) & df22["category_unified"].isin(CATS)]
    total = len(sub)
    all_vals_e1 += [sub["category_unified"].eq(c).sum() / total * 100 for c in CATS]

y_max = max(all_vals_e1) * 1.15

fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
fig.suptitle("Category Distribution by Platform — 2022\n(% of mapped rows, deduplicated by creator)",
             fontsize=13, fontweight="bold")

for ax, platform in zip(axes, platforms_e1):
    sub   = df22[(df22["platform"] == platform) & df22["category_unified"].isin(CATS)]
    total = len(sub)
    vals  = [sub["category_unified"].eq(c).sum() / total * 100 for c in CATS]
    x     = np.arange(len(CATS))
    bars  = ax.bar(x, vals, color=PLATFORM_COLORS[platform], alpha=0.85, edgecolor="white")
    annotate_dominant(ax, bars, vals)
    ax.set_title(platform, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(CATS, rotation=40, ha="right", fontsize=9)
    ax.set_ylabel("% of mapped rows")
    ax.set_ylim(0, y_max)

plt.tight_layout()
plt.savefig(OUT / "E1_crossplatform_2022.png", bbox_inches="tight")
plt.close()
print("✅ E1 saved")

# ============================================================
# E2-E4. Cross-year per platform
# ============================================================
cross_year_configs = [
    ("Instagram", [(df22, 2022), (df24, 2024)]),
    ("TikTok",    [(df24, 2024)]),
    ("YouTube",   [(df22, 2022), (df24, 2024), (df26, 2026)]),
]

for platform, year_dfs in cross_year_configs:
    all_pcts = []
    for df, year in year_dfs:
        sub   = df[(df["platform"] == platform) & df["category_unified"].isin(CATS)]
        total = len(sub)
        if total > 0:
            all_pcts += [sub["category_unified"].eq(c).sum() / total * 100 for c in CATS]

    if not all_pcts:
        continue

    y_max = max(all_pcts) * 1.15
    n     = len(year_dfs)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 6), sharey=True)
    if n == 1:
        axes = [axes]

    fig.suptitle(f"{platform} — Category Distribution Across Years\n(% of mapped rows, deduplicated by creator)",
                 fontsize=13, fontweight="bold")

    for ax, (df, year) in zip(axes, year_dfs):
        sub   = df[(df["platform"] == platform) & df["category_unified"].isin(CATS)]
        total = len(sub)
        if total == 0:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(str(year), fontweight="bold")
            continue
        vals = [sub["category_unified"].eq(c).sum() / total * 100 for c in CATS]
        x    = np.arange(len(CATS))
        bars = ax.bar(x, vals, color=YEAR_COLORS.get(year, "#999"),
                      alpha=0.85, edgecolor="white")
        annotate_dominant(ax, bars, vals)
        ax.set_title(str(year), fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(CATS, rotation=40, ha="right", fontsize=9)
        ax.set_ylabel("% of mapped rows")
        ax.set_ylim(0, y_max)

    plt.tight_layout()
    label = {"Instagram": "E2", "TikTok": "E3", "YouTube": "E4"}[platform]
    plt.savefig(OUT / f"{label}_crossyear_{platform.lower()}.png", bbox_inches="tight")
    plt.close()
    print(f"✅ {label} saved")

# ============================================================
# E5. Top 10 countries — organized by year
# ============================================================
rows_by_year = {
    2022: [("Instagram", df22), ("YouTube", df22)],
    2024: [("Instagram", top100_2024), ("TikTok", top100_2024), ("YouTube", top100_2024)],
    2026: [("YouTube", df26)],
}

year_xmax = {}
for year, combos in rows_by_year.items():
    xmax = 0
    for platform, df in combos:
        sub = df[(df["platform"] == platform) & df["audience_country"].notna()]
        if len(sub):
            xmax = max(xmax, sub["audience_country"].value_counts().iloc[0])
    year_xmax[year] = xmax

fig, axes = plt.subplots(3, 3, figsize=(18, 18))
fig.suptitle("Top 10 Audience Countries by Platform and Year\n"
             "(TikTok 2022 excluded — no country data; 2024 based on top 100 by followers)",
             fontsize=13, fontweight="bold")

for row_idx, (year, combos) in enumerate(rows_by_year.items()):
    for col_idx, (platform, df) in enumerate(combos):
        ax    = axes[row_idx][col_idx]
        sub   = df[(df["platform"] == platform) & df["audience_country"].notna()]
        top10 = sub["audience_country"].value_counts().head(10)
        color = PLATFORM_COLORS.get(platform, "#999")
        ax.barh(top10.index[::-1], top10.values[::-1],
                color=color, alpha=0.85, edgecolor="white")
        ax.set_title(f"{platform} {year}", fontweight="bold")
        ax.set_xlabel("Creator count")
        ax.set_xlim(0, year_xmax[year] * 1.1)
    for col_idx in range(len(combos), 3):
        axes[row_idx][col_idx].set_visible(False)

plt.tight_layout()
plt.savefig(OUT / "E5_country_top10.png", bbox_inches="tight")
plt.close()
print("✅ E5 saved")

# ============================================================
# E6. Country coverage
# ============================================================
coverage_rows = []
for platform in ["Instagram", "TikTok", "YouTube"]:
    for df, year in [(df22, 2022), (top100_2024, 2024), (df26, 2026)]:
        if platform == "TikTok" and year == 2022:
            continue
        sub = df[df["platform"] == platform]
        if len(sub) == 0:
            continue
        n = sub["audience_country"].dropna().nunique()
        coverage_rows.append({"platform": platform, "year": year, "n_countries": n})

cov_df = pd.DataFrame(coverage_rows)
fig, ax = plt.subplots(figsize=(10, 5))
for platform in ["Instagram", "TikTok", "YouTube"]:
    sub = cov_df[cov_df["platform"] == platform].sort_values("year")
    if sub.empty:
        continue
    ax.plot(sub["year"], sub["n_countries"], marker="o",
            color=PLATFORM_COLORS[platform],
            label=platform, linewidth=2, markersize=8)
    for _, row in sub.iterrows():
        ax.annotate(str(int(row["n_countries"])),
                    (row["year"], row["n_countries"]),
                    textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=9)

ax.set_title("Unique Countries Represented per Platform per Year\n"
             "(TikTok 2022 excluded; 2024 based on top 100 by followers)",
             fontweight="bold")
ax.set_xlabel("Year")
ax.set_ylabel("Number of unique countries")
ax.set_xticks([2022, 2024, 2026])
ax.legend()
plt.tight_layout()
plt.savefig(OUT / "E6_country_coverage.png", bbox_inches="tight")
plt.close()
print("✅ E6 saved")

# ============================================================
# E7. Follower distribution — separate subplot per platform-year
# ============================================================
BINS = np.linspace(3, 9, 31)

# Only valid combos
combos_e7 = [
    ("Instagram", 2022, df22), ("TikTok", 2022, df22), ("YouTube", 2022, df22),
    ("Instagram", 2024, df24), ("TikTok", 2024, df24), ("YouTube", 2024, df24),
    ("YouTube",   2026, df26),
]

fig, axes = plt.subplots(3, 3, figsize=(18, 14))
fig.suptitle("Follower Count Distribution by Platform and Year (log₁₀ scale)",
             fontsize=14, fontweight="bold")
axes_flat = axes.flatten()

for idx, (platform, year, df) in enumerate(combos_e7):
    ax  = axes_flat[idx]
    sub = df[(df["platform"] == platform) & df["followers"].notna() & (df["followers"] > 0)]
    vals = np.log10(sub["followers"].dropna())
    ax.hist(vals, bins=BINS, color=YEAR_COLORS.get(year, "#999"),
            alpha=0.85, edgecolor="white")
    ax.set_title(f"{platform} — {year}", fontweight="bold")
    ax.set_xlabel("log₁₀(followers)")
    ax.set_ylabel("Count")
    ax.set_xlim(3, 9)
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"$10^{{{int(x)}}}$" if x == int(x) else "")
    )

# Hide unused subplots
for idx in range(len(combos_e7), len(axes_flat)):
    axes_flat[idx].set_visible(False)

plt.tight_layout()
plt.savefig(OUT / "E7_followers_distribution.png", bbox_inches="tight")
plt.close()
print("✅ E7 saved")

# ============================================================
# E8. ER box plots — 2024 top 100 by followers
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))
data_for_box = []
labels       = []

for platform in ["Instagram", "TikTok", "YouTube"]:
    sub = top100_2024[(top100_2024["platform"] == platform) &
                      top100_2024["er_pct"].notna() &
                      (top100_2024["er_pct"] > 0)]
    if len(sub):
        data_for_box.append(sub["er_pct"].values)
        labels.append(platform)

bp = ax.boxplot(data_for_box, labels=labels, patch_artist=True,
                medianprops={"color": "black", "linewidth": 2},
                flierprops={"marker": "o", "markersize": 4, "alpha": 0.4})

for patch, platform in zip(bp["boxes"], labels):
    patch.set_facecolor(PLATFORM_COLORS.get(platform, "#999"))
    patch.set_alpha(0.7)

ax.set_title("Engagement Rate Distribution by Platform — 2024\n(Top 100 creators by followers)",
             fontweight="bold")
ax.set_ylabel("Engagement Rate (%)")
ax.set_xlabel("")
plt.tight_layout()
plt.savefig(OUT / "E8_er_boxplots_2024.png", bbox_inches="tight")
plt.close()
print("✅ E8 saved")

# ============================================================
# E9. Missing data heatmap — NaN rates for key columns
# ============================================================
miss_rows = []
configs_miss = [
    ("Instagram", 2022, df22), ("YouTube", 2022, df22),
    ("Instagram", 2024, df24), ("TikTok", 2024, df24), ("YouTube", 2024, df24),
    ("YouTube", 2026, df26),
]
for platform, year, df in configs_miss:
    sub = df[df["platform"] == platform]
    total = len(sub)
    if total == 0:
        continue
    miss_rows.append({
        "Platform / Year": f"{platform}\n{year}",
        "category_unified": sub["category_unified"].isna().sum() / total * 100,
        "audience_country": sub["audience_country"].isna().sum() / total * 100,
    })

miss_df  = pd.DataFrame(miss_rows).set_index("Platform / Year")

fig, ax = plt.subplots(figsize=(10, 5))
sns.heatmap(miss_df.T, annot=True, fmt=".1f", cmap="Reds",
            linewidths=0.5, linecolor="white",
            cbar_kws={"label": "% missing"}, ax=ax)
ax.set_title("Missing Data Rates by Platform and Year (%) \n (TikTok 2022 excluded — no category or country data)",
             fontweight="bold")
ax.set_xlabel("")
ax.set_ylabel("")
plt.tight_layout()
plt.savefig(OUT / "E9_missing_data_heatmap.png", bbox_inches="tight")
plt.close()
print("✅ E9 saved")

# ============================================================
# E10. Stacked bar — category proportions all platform-years
# ============================================================
CAT_COLORS_MAP = {
    "Entertainment":  "#FF6B6B",
    "Music":          "#4ECDC4",
    "Sports":         "#45B7D1",
    "Beauty&Fashion": "#F7DC6F",
    "Tech&Gaming":    "#BB8FCE",
    "Knowledge&Info": "#82E0AA",
    "Lifestyle":      "#F0B27A",
}

stacked_rows = []
configs_stack = [
    ("Instagram", 2022, df22), ("YouTube", 2022, df22),
    ("Instagram", 2024, df24), ("TikTok", 2024, df24), ("YouTube", 2024, df24),
    ("YouTube", 2026, df26),
]
for platform, year, df in configs_stack:
    sub   = df[(df["platform"] == platform) & df["category_unified"].isin(CATS)]
    total = len(sub)
    if total == 0:
        continue
    row = {"label": f"{platform}\n{year}"}
    for cat in CATS:
        row[cat] = sub["category_unified"].eq(cat).sum() / total * 100
    stacked_rows.append(row)

stack_df = pd.DataFrame(stacked_rows).set_index("label")

fig, ax = plt.subplots(figsize=(13, 6))
stack_df[CATS].plot(kind="bar", stacked=True, ax=ax,
                    color=[CAT_COLORS_MAP[c] for c in CATS],
                    edgecolor="white", alpha=0.9, width=0.7)
ax.set_title("Category Composition by Platform and Year (% of mapped rows, deduplicated by creator)",
             fontweight="bold")
ax.set_xlabel("")
ax.set_ylabel("% of mapped rows")
ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right")
ax.legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9)
plt.tight_layout()
plt.savefig(OUT / "E10_stacked_category_bar.png", bbox_inches="tight")
plt.close()
print("✅ E10 saved")

print(f"\n✅ All figures saved to {OUT.resolve()}")