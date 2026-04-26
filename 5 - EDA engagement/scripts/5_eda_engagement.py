"""
Step 5: EDA on engagement_total and er_pct

Input:  4 - ER calculation/finalData_with_er.csv
Output: 5 - EDA engagement/plots/*.png
        5 - EDA engagement/summary_stats.txt
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
SRC  = ROOT / "4 - ER unified" / "finalData_with_er.csv"
OUT  = ROOT / "5 - EDA engagement"
PLOT = OUT / "plots"
PLOT.mkdir(exist_ok=True, parents=True)

df = pd.read_csv(SRC, low_memory=False)
df["slice"] = df["_platform"].str.capitalize() + " " + df["_year"].astype(str)

PLATFORM_COLOR = {"instagram": "#E4405F", "tiktok": "#000000", "youtube": "#FF0000"}

summary_lines = []
def log(msg):
    print(msg)
    summary_lines.append(msg)

log(f"Rows: {len(df):,}")
log(f"engagement_total non-null: {df['engagement_total'].notna().sum():,}")
log(f"er_pct non-null:           {df['er_pct'].notna().sum():,}")

# ==========================================================================
# P1: Distribution of engagement_total (IG 2022 only — this column is IG-2022 specific)
# ==========================================================================
ig22 = df[(df["_platform"] == "instagram") & (df["_year"] == 2022) & df["engagement_total"].notna()]
fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(np.log10(ig22["engagement_total"]), bins=50, color=PLATFORM_COLOR["instagram"], alpha=0.8)
ax.set_xlabel("log10(engagement_total)")
ax.set_ylabel("Count of accounts")
ax.set_title(f"Distribution of engagement_total — Instagram 2022 (n={len(ig22):,})")
ax.axvline(np.log10(ig22["engagement_total"].median()), color="black", ls="--",
           label=f"median = {ig22['engagement_total'].median():,.0f}")
ax.legend()
fig.tight_layout()
fig.savefig(PLOT / "P1_engagement_total_distribution.png", dpi=140)
plt.close(fig)

log("\n--- engagement_total (IG 2022) ---")
log(ig22["engagement_total"].describe().round(2).to_string())

# ==========================================================================
# P2: Distribution of er_pct per platform × year (log-x, faceted)
# ==========================================================================
slices = [("instagram", 2022), ("instagram", 2024),
          ("tiktok",    2022), ("tiktok",    2024),
          ("youtube",   2022), ("youtube",   2024), ("youtube", 2026)]

fig, axes = plt.subplots(2, 4, figsize=(16, 8), sharey=False)
axes = axes.flatten()
for ax, (plat, yr) in zip(axes, slices):
    sub = df[(df["_platform"] == plat) & (df["_year"] == yr)
             & df["er_pct"].notna() & (df["er_pct"] > 0)]
    if len(sub) == 0:
        ax.set_visible(False); continue
    ax.hist(np.log10(sub["er_pct"]), bins=40, color=PLATFORM_COLOR[plat], alpha=0.8)
    med = sub["er_pct"].median()
    ax.axvline(np.log10(med), color="black", ls="--", lw=1)
    ax.set_title(f"{plat.capitalize()} {yr} (n={len(sub):,}, med={med:.2f}%)")
    ax.set_xlabel("log10(er_pct %)")
    ax.set_ylabel("Count")
axes[-1].set_visible(False)
fig.suptitle("er_pct distribution by platform × year", y=1.00)
fig.tight_layout()
fig.savefig(PLOT / "P2_er_pct_distribution_by_slice.png", dpi=140)
plt.close(fig)

log("\n--- er_pct by platform × year ---")
log(df.groupby(["_platform", "_year"])["er_pct"].describe().round(2).to_string())

# ==========================================================================
# P3: Boxplot of er_pct by platform × year (log-y, easier cross-slice view)
# ==========================================================================
box_data, labels, colors = [], [], []
for plat, yr in slices:
    sub = df[(df["_platform"] == plat) & (df["_year"] == yr)
             & df["er_pct"].notna() & (df["er_pct"] > 0)]
    if len(sub) == 0: continue
    box_data.append(np.log10(sub["er_pct"].values))
    labels.append(f"{plat[:2].capitalize()} {yr}")
    colors.append(PLATFORM_COLOR[plat])

fig, ax = plt.subplots(figsize=(10, 5))
bp = ax.boxplot(box_data, labels=labels, patch_artist=True, showfliers=False)
for patch, c in zip(bp["boxes"], colors):
    patch.set_facecolor(c); patch.set_alpha(0.6)
ax.set_ylabel("log10(er_pct %)")
ax.set_title("Engagement rate (er_pct) across platforms × years")
ax.axhline(0, color="gray", lw=0.5, ls=":")  # 1%
fig.tight_layout()
fig.savefig(PLOT / "P3_er_pct_boxplot_by_slice.png", dpi=140)
plt.close(fig)

# ==========================================================================
# P4: Followers vs engagement_count scatter (log-log) by platform — uses 2022 where we have full data
# ==========================================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)
for ax, plat in zip(axes, ["instagram", "tiktok", "youtube"]):
    sub = df[(df["_platform"] == plat) & (df["_year"] == 2022)
             & df["engagement_count"].notna() & df["followers"].notna()
             & (df["engagement_count"] > 0) & (df["followers"] > 0)]
    ax.scatter(np.log10(sub["followers"]), np.log10(sub["engagement_count"]),
               s=6, alpha=0.3, color=PLATFORM_COLOR[plat])
    if len(sub) > 5:
        b, a = np.polyfit(np.log10(sub["followers"]), np.log10(sub["engagement_count"]), 1)
        xs = np.linspace(np.log10(sub["followers"]).min(), np.log10(sub["followers"]).max(), 100)
        ax.plot(xs, a + b * xs, color="black", lw=1.5, label=f"slope β={b:.2f}")
        ax.legend()
    ax.set_title(f"{plat.capitalize()} 2022 (n={len(sub):,})")
    ax.set_xlabel("log10(followers)")
    ax.set_ylabel("log10(engagement_count)")
fig.suptitle("Followers vs engagement_count (log-log) — 2022", y=1.00)
fig.tight_layout()
fig.savefig(PLOT / "P4_followers_vs_engagement_loglog.png", dpi=140)
plt.close(fig)

# ==========================================================================
# P5: er_pct by category — across all slices with enough coverage
# (TikTok 2022 has no category data; YT 2024 has only 120 labelled rows → skipped)
# ==========================================================================
cat_slices = [("instagram", 2022), ("instagram", 2024),
              ("youtube",   2022), ("youtube",   2026)]

fig, axes = plt.subplots(2, 2, figsize=(14, 9))
axes = axes.flatten()
for ax, (plat, yr) in zip(axes, cat_slices):
    sub = df[(df["_platform"] == plat) & (df["_year"] == yr)
             & df["er_pct"].notna() & (df["er_pct"] > 0)
             & df["category_unified"].notna()].copy()
    sub["log_er"] = np.log10(sub["er_pct"])
    order = sub.groupby("category_unified")["log_er"].median().sort_values().index.tolist()
    data = [sub[sub["category_unified"] == c]["log_er"].values for c in order]
    bp = ax.boxplot(data, labels=order, patch_artist=True, showfliers=False)
    for patch in bp["boxes"]:
        patch.set_facecolor(PLATFORM_COLOR[plat]); patch.set_alpha(0.6)
    ax.set_ylabel("log10(er_pct %)")
    ax.set_title(f"{plat.capitalize()} {yr}  (n={len(sub):,})")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
fig.suptitle("er_pct by content category — across platforms & years", y=1.00)
fig.tight_layout()
fig.savefig(PLOT / "P5_er_pct_by_category.png", dpi=140)
plt.close(fig)

log("\n--- er_pct by category (median, per slice) ---")
for plat, yr in cat_slices:
    sub = df[(df["_platform"] == plat) & (df["_year"] == yr)
             & df["er_pct"].notna() & (df["er_pct"] > 0)
             & df["category_unified"].notna()]
    log(f"\n{plat.capitalize()} {yr}:")
    log(sub.groupby("category_unified")["er_pct"].median().round(2).sort_values().to_string())

# ==========================================================================
# P6: er_pct by country (IG 2022, top N by count)
# ==========================================================================
cn = df[(df["_platform"] == "instagram") & (df["_year"] == 2022)
        & df["er_pct"].notna() & (df["er_pct"] > 0)
        & df["country"].notna()].copy()
cn["log_er"] = np.log10(cn["er_pct"])
top_countries = cn["country"].value_counts().head(15).index.tolist()
cn = cn[cn["country"].isin(top_countries)]
country_order = cn.groupby("country")["log_er"].median().sort_values().index.tolist()

fig, ax = plt.subplots(figsize=(11, 5))
data = [cn[cn["country"] == c]["log_er"].values for c in country_order]
bp = ax.boxplot(data, labels=country_order, patch_artist=True, showfliers=False)
for patch in bp["boxes"]:
    patch.set_facecolor(PLATFORM_COLOR["instagram"]); patch.set_alpha(0.6)
ax.set_ylabel("log10(er_pct %)")
ax.set_title("Instagram 2022: er_pct by audience country (top 15 by sample size)")
plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
fig.tight_layout()
fig.savefig(PLOT / "P6_er_pct_by_country_ig2022.png", dpi=140)
plt.close(fig)

# ==========================================================================
# P7: Correlation between followers and er_pct (do bigger accounts have lower ER?)
# ==========================================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)
for ax, plat in zip(axes, ["instagram", "tiktok", "youtube"]):
    sub = df[(df["_platform"] == plat) & (df["_year"] == 2022)
             & df["er_pct"].notna() & df["followers"].notna()
             & (df["er_pct"] > 0) & (df["followers"] > 0)]
    ax.scatter(np.log10(sub["followers"]), np.log10(sub["er_pct"]),
               s=6, alpha=0.3, color=PLATFORM_COLOR[plat])
    if len(sub) > 5:
        r = np.corrcoef(np.log10(sub["followers"]), np.log10(sub["er_pct"]))[0, 1]
        ax.text(0.05, 0.95, f"Pearson r = {r:.3f}\nn = {len(sub):,}",
                transform=ax.transAxes, va="top",
                bbox=dict(facecolor="white", edgecolor="gray"))
    ax.set_title(f"{plat.capitalize()} 2022")
    ax.set_xlabel("log10(followers)")
    ax.set_ylabel("log10(er_pct %)")
fig.suptitle("Do bigger accounts engage less? followers vs er_pct (log-log) — 2022", y=1.00)
fig.tight_layout()
fig.savefig(PLOT / "P7_followers_vs_er_loglog.png", dpi=140)
plt.close(fig)

# ==========================================================================
# P8: Component dominance — does views/likes/comments dominate engagement_count?
# Only slices where engagement_count is built from a sum: TT 2022, YT 2022, YT 2026
# ==========================================================================
sum_slices = [("tiktok", 2022), ("youtube", 2022), ("youtube", 2026)]
comps = ["views_avg", "likes_avg", "comments_avg", "shares_avg"]
comp_labels = ["views", "likes", "comments", "shares"]
comp_colors = ["#4C72B0", "#55A868", "#C44E52", "#8172B2"]

slice_labels, slice_means, slice_n = [], [], []
for plat, yr in sum_slices:
    sub = df[(df["_platform"] == plat) & (df["_year"] == yr)
             & df["engagement_count"].notna() & (df["engagement_count"] > 0)].copy()
    for c in comps:
        sub[c] = sub[c].fillna(0)
    total = sub[comps].sum(axis=1).replace(0, np.nan)
    shares = sub[comps].div(total, axis=0).dropna()
    slice_labels.append(f"{plat.capitalize()} {yr}")
    slice_means.append(shares.mean().values)
    slice_n.append(len(shares))
    log(f"\n--- {plat.capitalize()} {yr}: mean share of engagement_count ---")
    log(shares.mean().round(3).to_string())

means = np.array(slice_means)  # rows = slices, cols = components
y = np.arange(len(slice_labels))

fig, ax = plt.subplots(figsize=(11, 4.5))
left = np.zeros(len(slice_labels))
for j, (label, color) in enumerate(zip(comp_labels, comp_colors)):
    ax.barh(y, means[:, j], left=left, color=color, edgecolor="white",
            label=label, height=0.65)
    for i, v in enumerate(means[:, j]):
        if v >= 0.03:
            ax.text(left[i] + v / 2, y[i], f"{v*100:.1f}%",
                    ha="center", va="center", fontsize=9,
                    color="white" if j == 0 else "black")
    left += means[:, j]

ax.set_yticks(y)
ax.set_yticklabels([f"{lab}\n(n={n:,})" for lab, n in zip(slice_labels, slice_n)])
ax.set_xlim(0, 1)
ax.set_xlabel("Mean share of engagement_count")
ax.set_title("Views dominate engagement_count on TT/YT sum-based slices")
ax.legend(loc="lower right", ncol=4, frameon=False, bbox_to_anchor=(1, -0.25))
ax.invert_yaxis()
fig.tight_layout()
fig.savefig(PLOT / "P8_component_shares.png", dpi=140)
plt.close(fig)

# ==========================================================================
# Save summary
# ==========================================================================
(OUT / "summary_stats.txt").write_text("\n".join(summary_lines))
print(f"\nWrote {len(list(PLOT.glob('*.png')))} plots to {PLOT}")
print(f"Wrote summary to {OUT/'summary_stats.txt'}")
