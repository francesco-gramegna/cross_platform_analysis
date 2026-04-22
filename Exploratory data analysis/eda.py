"""
Cross-Platform Influencer EDA
Outputs: numerical summaries (CSV/TXT) + visualizations (PNG)
"""

import warnings
warnings.filterwarnings("ignore")

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats

# ── paths ──────────────────────────────────────────────────────────────────────
BASE   = os.path.dirname(os.path.abspath(__file__))
DATA   = os.path.join(BASE, "..", "cleaned_dataset", "updated")
OUT    = BASE                        # save everything next to this script
FIGS   = os.path.join(OUT, "figures")
NUMS   = os.path.join(OUT, "numerical_summaries")
os.makedirs(FIGS, exist_ok=True)
os.makedirs(NUMS, exist_ok=True)

PALETTE = {"Instagram": "#C13584", "TikTok": "#010101", "YouTube": "#FF0000"}
sns.set_theme(style="whitegrid", font_scale=1.1)

# ── helpers ────────────────────────────────────────────────────────────────────
def savefig(name, tight=True):
    path = os.path.join(FIGS, name)
    if tight:
        plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  saved → figures/{name}")

def savecsv(df, name):
    path = os.path.join(NUMS, name)
    df.to_csv(path)
    print(f"  saved → numerical_summaries/{name}")

# ══════════════════════════════════════════════════════════════════════════════
# 1. LOAD & HARMONISE
# ══════════════════════════════════════════════════════════════════════════════
print("\n[1] Loading datasets …")

df22 = pd.read_csv(os.path.join(DATA, "merged_2022_all.csv"))
df24 = pd.read_csv(os.path.join(DATA, "merged_2024_all.csv"))
df26 = pd.read_csv(os.path.join(DATA, "merged_2026.csv"))

# All three files already have unified column names after cleaning.
# Just cast numeric columns and create aliases used downstream.
for df in [df22, df24, df26]:
    df["followers"] = pd.to_numeric(df["followers"], errors="coerce")
    df["er_pct"]    = pd.to_numeric(df["er_pct"],    errors="coerce")
    df["category"]  = df["category_unified"]
    df["country"]   = df["audience_country"]

KEEP = ["year", "platform", "category", "country", "followers", "er_pct"]
df22k = df22[KEEP].copy()
df24k = df24[KEEP].copy()
df26k = df26[KEEP].copy()
all_df = pd.concat([df22k, df24k, df26k], ignore_index=True)

# follower tiers
def follower_tier(f):
    if pd.isna(f):   return np.nan
    if f < 1e4:      return "Nano (<10K)"
    if f < 1e5:      return "Micro (10K–100K)"
    if f < 1e6:      return "Macro (100K–1M)"
    if f < 1e7:      return "Mega (1M–10M)"
    return                   "Top (>10M)"

TIER_ORDER = ["Nano (<10K)", "Micro (10K–100K)", "Macro (100K–1M)",
              "Mega (1M–10M)", "Top (>10M)"]
all_df["tier"] = all_df["followers"].apply(follower_tier)
all_df["tier"] = pd.Categorical(all_df["tier"], categories=TIER_ORDER, ordered=True)

print("  Combined rows:", len(all_df))

# ══════════════════════════════════════════════════════════════════════════════
# 2. NUMERICAL SUMMARIES
# ══════════════════════════════════════════════════════════════════════════════
print("\n[2] Numerical summaries …")

# 2-A  Dataset overview
overview_rows = []
for yr, sub in [(2022, df22k), (2024, df24k), (2026, df26k)]:
    for plat, grp in sub.groupby("platform"):
        overview_rows.append({
            "year": yr, "platform": plat,
            "n_influencers":   len(grp),
            "median_followers": grp["followers"].median(),
            "mean_followers":   grp["followers"].mean(),
            "median_er_pct":    grp["er_pct"].median(),
            "mean_er_pct":      grp["er_pct"].mean(),
            "missing_er_pct":   grp["er_pct"].isna().sum(),
        })
overview = pd.DataFrame(overview_rows)
savecsv(overview, "01_dataset_overview.csv")

# 2-B  Follower descriptive stats by year × platform
follower_stats = (
    all_df.groupby(["year", "platform"])["followers"]
    .describe(percentiles=[.25, .5, .75, .9, .99])
    .round(0)
)
savecsv(follower_stats, "02_follower_stats_by_year_platform.csv")

# 2-C  ER descriptive stats
er_stats = (
    all_df.dropna(subset=["er_pct"])
    .groupby(["year", "platform"])["er_pct"]
    .describe(percentiles=[.25, .5, .75, .9])
    .round(4)
)
savecsv(er_stats, "03_er_stats_by_year_platform.csv")

# 2-D  Category distribution
cat_dist = (
    all_df.groupby(["year", "platform", "category"])
    .size().reset_index(name="count")
)
cat_dist["pct"] = cat_dist.groupby(["year", "platform"])["count"].transform(
    lambda x: x / x.sum() * 100
).round(2)
savecsv(cat_dist, "04_category_distribution.csv")

# 2-E  Top 10 audience countries per year
for yr, sub in [(2022, df22k), (2024, df24k)]:
    top_c = sub["country"].value_counts().head(10).reset_index()
    top_c.columns = ["country", "count"]
    savecsv(top_c, f"05_top_countries_{yr}.csv")

# 2-F  Median ER by follower tier × platform
tier_er = (
    all_df.dropna(subset=["er_pct", "tier"])
    .groupby(["year", "platform", "tier"])["er_pct"]
    .agg(["median", "mean", "count"])
    .round(4)
)
savecsv(tier_er, "06_er_by_tier_platform_year.csv")

# 2-G  Category ER variance (for RQ4 – AI convergence)
cat_er_var = (
    all_df.dropna(subset=["er_pct"])
    .groupby(["year", "category"])["er_pct"]
    .agg(["std", "var", "median", "count"])
    .round(4)
)
savecsv(cat_er_var, "07_category_er_variance_by_year.csv")

# ══════════════════════════════════════════════════════════════════════════════
# 3. VISUALISATIONS
# ══════════════════════════════════════════════════════════════════════════════
print("\n[3] Figures …")

# ── FIG 1: Dataset size (bar chart) ───────────────────────────────────────────
print("  Fig 1: Dataset size …")
fig, ax = plt.subplots(figsize=(8, 4))
plot_df = overview.copy()
plot_df["label"] = plot_df["year"].astype(str) + "\n" + plot_df["platform"]
colors = [PALETTE.get(p, "steelblue") for p in plot_df["platform"]]
bars = ax.bar(plot_df["label"], plot_df["n_influencers"], color=colors, edgecolor="white", linewidth=0.8)
for bar, val in zip(bars, plot_df["n_influencers"]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 80,
            f"{int(val):,}", ha="center", va="bottom", fontsize=9)
ax.set_title("Number of Influencers per Platform per Year", fontweight="bold")
ax.set_ylabel("Count")
ax.set_xlabel("")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
savefig("01_dataset_size.png")

# ── FIG 2: Follower distribution (log-scale KDE, by platform & year) ──────────
print("  Fig 2: Follower distribution …")
years  = [2022, 2024, 2026]
fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=False)
for ax, yr in zip(axes, years):
    sub = all_df[all_df["year"] == yr].dropna(subset=["followers"])
    sub = sub[sub["followers"] > 0]
    for plat, grp in sub.groupby("platform"):
        log_f = np.log10(grp["followers"])
        log_f = log_f[np.isfinite(log_f)]
        if len(log_f) < 5:
            continue
        sns.kdeplot(log_f, ax=ax, label=plat, color=PALETTE.get(plat, "gray"),
                    fill=True, alpha=0.25, linewidth=1.8)
    ax.set_title(f"{yr}", fontweight="bold")
    ax.set_xlabel("log₁₀(Followers)")
    ax.set_ylabel("Density" if yr == 2022 else "")
    xticks = [4, 5, 6, 7, 8, 9]
    ax.set_xticks(xticks)
    ax.set_xticklabels([f"10^{t}" for t in xticks], fontsize=8)
    ax.legend(fontsize=8)
fig.suptitle("Follower Distribution by Platform and Year (log scale)", fontweight="bold", y=1.01)
savefig("02_follower_distribution_log.png")

# ── FIG 3: Follower tier composition (stacked bar) ────────────────────────────
print("  Fig 3: Follower tier composition …")
tier_count = (
    all_df.dropna(subset=["tier"])
    .groupby(["year", "platform", "tier"])
    .size().reset_index(name="count")
)
tier_pct = tier_count.copy()
tier_pct["pct"] = tier_pct.groupby(["year", "platform"])["count"].transform(
    lambda x: x / x.sum() * 100
)
tier_pct["label"] = tier_pct["year"].astype(str) + "\n" + tier_pct["platform"]
label_order = tier_pct.drop_duplicates("label").sort_values(["year", "platform"])["label"].tolist()

tier_pct_pivot = tier_pct.pivot_table(
    index="label", columns="tier", values="pct", aggfunc="sum"
).reindex(index=label_order, columns=TIER_ORDER).fillna(0)

tier_colors = sns.color_palette("Blues_r", n_colors=len(TIER_ORDER))
fig, ax = plt.subplots(figsize=(12, 5))
tier_pct_pivot.plot(kind="bar", stacked=True, ax=ax, color=tier_colors, edgecolor="white", linewidth=0.5)
ax.set_title("Follower Tier Composition by Platform and Year", fontweight="bold")
ax.set_ylabel("Percentage (%)")
ax.set_xlabel("")
ax.set_xticklabels(label_order, rotation=0, fontsize=9)
ax.legend(title="Tier", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
savefig("03_follower_tier_composition.png")

# ── FIG 4: Engagement rate box plots (by platform × year) ─────────────────────
print("  Fig 4: ER box plots …")
er_plot = all_df.dropna(subset=["er_pct"])
er_plot = er_plot[(er_plot["er_pct"] >= 0) & (er_plot["er_pct"] <= 50)]  # clip extreme outliers
fig, ax = plt.subplots(figsize=(10, 5))
sns.boxplot(
    data=er_plot, x="platform", y="er_pct", hue="year",
    palette="Set2", width=0.5, linewidth=0.8,
    flierprops=dict(marker="o", markersize=2, alpha=0.3),
    ax=ax
)
ax.set_title("Engagement Rate (%) by Platform and Year", fontweight="bold")
ax.set_ylabel("Engagement Rate (%)")
ax.set_xlabel("")
ax.legend(title="Year", fontsize=9)
savefig("04_er_boxplot_platform_year.png")

# ── FIG 5: Category share per platform per year (heatmap) ─────────────────────
print("  Fig 5: Category × platform heatmap …")
cat_pivot = (
    all_df.dropna(subset=["category"])
    .groupby(["year", "platform", "category"])
    .size()
    .reset_index(name="n")
)
cat_pivot["pct"] = cat_pivot.groupby(["year", "platform"])["n"].transform(
    lambda x: x / x.sum() * 100
)
cat_pivot["year_platform"] = cat_pivot["year"].astype(str) + " " + cat_pivot["platform"]

hm = cat_pivot.pivot_table(index="category", columns="year_platform", values="pct", aggfunc="sum").fillna(0)
# sort columns chronologically
col_order = sorted(hm.columns, key=lambda s: (int(s.split()[0]), s.split()[1]))
hm = hm[col_order]
# sort rows by total share
hm = hm.loc[hm.sum(axis=1).sort_values(ascending=False).index]

fig, ax = plt.subplots(figsize=(13, 6))
sns.heatmap(hm, annot=True, fmt=".1f", cmap="YlOrRd", linewidths=0.4,
            cbar_kws={"label": "% of platform-year"}, ax=ax)
ax.set_title("Content Category Share (%) per Platform per Year", fontweight="bold")
ax.set_xlabel("")
ax.set_ylabel("Category")
plt.xticks(rotation=30, ha="right", fontsize=9)
savefig("05_category_heatmap.png")

# ── FIG 6: Category distribution stacked bar (per year, all platforms) ────────
print("  Fig 6: Category stacked bar …")
cat_year = (
    all_df.dropna(subset=["category"])
    .groupby(["year", "category"])
    .size().reset_index(name="count")
)
cat_year["pct"] = cat_year.groupby("year")["count"].transform(
    lambda x: x / x.sum() * 100
)
cat_pivot2 = cat_year.pivot_table(index="year", columns="category", values="pct", aggfunc="sum").fillna(0)
# order categories by total
cat_order2 = cat_pivot2.sum().sort_values(ascending=False).index.tolist()
cat_pivot2 = cat_pivot2[cat_order2]

fig, ax = plt.subplots(figsize=(9, 5))
cat_pivot2.plot(kind="bar", stacked=True, ax=ax,
                colormap="tab10", edgecolor="white", linewidth=0.5)
ax.set_title("Content Category Mix by Year (all platforms)", fontweight="bold")
ax.set_ylabel("Percentage (%)")
ax.set_xlabel("Year")
ax.set_xticklabels([str(y) for y in cat_pivot2.index], rotation=0)
ax.legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
savefig("06_category_stacked_bar_year.png")

# ── FIG 7: Top 15 audience countries – 2022 ───────────────────────────────────
print("  Fig 7: Top countries 2022 …")
top_c22 = df22k["country"].value_counts().head(15).reset_index()
top_c22.columns = ["country", "count"]
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.barh(top_c22["country"][::-1], top_c22["count"][::-1],
               color="#4C72B0", edgecolor="white")
for bar, val in zip(bars, top_c22["count"][::-1]):
    ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height()/2,
            f"{int(val):,}", va="center", fontsize=8)
ax.set_title("Top 15 Audience Countries — 2022", fontweight="bold")
ax.set_xlabel("Number of Influencers")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
savefig("07_top_countries_2022.png")

# ── FIG 8: Micro-influencer ER — median ER by tier × platform (2022 & 2024) ──
print("  Fig 8: Micro-influencer ER by tier …")
micro_df = all_df[all_df["year"].isin([2022, 2024])].dropna(subset=["er_pct", "tier"])
micro_df = micro_df[(micro_df["er_pct"] >= 0) & (micro_df["er_pct"] <= 50)]

fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=False)
for ax, yr in zip(axes, [2022, 2024]):
    sub = micro_df[micro_df["year"] == yr]
    plats = sub["platform"].unique()
    for plat in plats:
        grp = sub[sub["platform"] == plat]
        med = grp.groupby("tier", observed=False)["er_pct"].median().reindex(TIER_ORDER)
        ax.plot(TIER_ORDER, med.values, marker="o", label=plat,
                color=PALETTE.get(plat, "gray"), linewidth=2)
    ax.set_title(f"{yr} — Median ER by Follower Tier", fontweight="bold")
    ax.set_ylabel("Median Engagement Rate (%)")
    ax.set_xlabel("Follower Tier")
    ax.tick_params(axis="x", labelrotation=20)
    ax.legend(fontsize=8)
fig.suptitle("Micro-Influencer Advantage: ER vs Follower Tier", fontweight="bold", y=1.01)
savefig("08_micro_influencer_er_by_tier.png")

# ── FIG 9: ER variance by category × year (RQ4 – AI convergence) ─────────────
print("  Fig 9: ER variance by category & year …")
var_df = all_df.dropna(subset=["er_pct"]).copy()
var_df = var_df[(var_df["er_pct"] >= 0) & (var_df["er_pct"] <= 50)]
cat_std = (
    var_df.groupby(["year", "category"])["er_pct"]
    .agg(["std", "count"])
    .reset_index()
)
# keep categories with enough data
valid_cats = cat_std[cat_std["count"] >= 30]["category"].value_counts()
valid_cats = valid_cats[valid_cats >= 2].index.tolist()
cat_std = cat_std[cat_std["category"].isin(valid_cats)]

cat_std_pivot = cat_std.pivot_table(index="category", columns="year", values="std")
cat_std_pivot = cat_std_pivot.dropna()

fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(cat_std_pivot))
width = 0.25
years_avail = [c for c in [2022, 2024, 2026] if c in cat_std_pivot.columns]
colors_var = ["#2196F3", "#FF9800", "#4CAF50"]
for i, (yr, col) in enumerate(zip(years_avail, colors_var)):
    ax.bar(x + i * width, cat_std_pivot[yr], width=width, label=str(yr),
           color=col, edgecolor="white", alpha=0.85)
ax.set_xticks(x + width)
ax.set_xticklabels(cat_std_pivot.index, rotation=25, ha="right", fontsize=9)
ax.set_title("Engagement Rate Std Dev by Category and Year\n(proxy for content convergence)", fontweight="bold")
ax.set_ylabel("Std Dev of ER (%)")
ax.legend(title="Year")
savefig("09_er_variance_by_category_year.png")

# ── FIG 10: Scatter — followers vs ER (log scale, colored by platform) ────────
print("  Fig 10: Followers vs ER scatter …")
scatter_df = all_df.dropna(subset=["followers", "er_pct"])
scatter_df = scatter_df[
    (scatter_df["followers"] > 1000) &
    (scatter_df["er_pct"] > 0) &
    (scatter_df["er_pct"] <= 30)
].copy()
scatter_df["log_followers"] = np.log10(scatter_df["followers"])

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
for ax, yr in zip(axes, [2022, 2024]):
    sub = scatter_df[scatter_df["year"] == yr]
    for plat, grp in sub.groupby("platform"):
        ax.scatter(grp["log_followers"], grp["er_pct"],
                   alpha=0.18, s=10, label=plat, color=PALETTE.get(plat, "gray"))
        # trend line
        if len(grp) > 20:
            z = np.polyfit(grp["log_followers"], grp["er_pct"], 1)
            p = np.poly1d(z)
            xs = np.linspace(grp["log_followers"].min(), grp["log_followers"].max(), 100)
            ax.plot(xs, p(xs), color=PALETTE.get(plat, "gray"), linewidth=2)
    ax.set_title(f"{yr} — Followers vs Engagement Rate", fontweight="bold")
    ax.set_xlabel("log₁₀(Followers)")
    ax.set_ylabel("Engagement Rate (%)")
    xticks = [4, 5, 6, 7, 8, 9]
    ax.set_xticks([t for t in xticks if scatter_df["log_followers"].min() <= t <= scatter_df["log_followers"].max()])
    ax.set_xticklabels([f"10^{t}" for t in xticks if scatter_df["log_followers"].min() <= t <= scatter_df["log_followers"].max()], fontsize=8)
    ax.legend(markerscale=3, fontsize=8)
fig.suptitle("Followers vs Engagement Rate (log scale) — Trend Lines by Platform",
             fontweight="bold", y=1.01)
savefig("10_followers_vs_er_scatter.png")

# ── FIG 11: ER by category × platform (2024, most complete) ──────────────────
print("  Fig 11: ER by category × platform 2024 …")
er24 = all_df[(all_df["year"] == 2024)].dropna(subset=["er_pct", "category"])
er24 = er24[(er24["er_pct"] >= 0) & (er24["er_pct"] <= 30)]
cat_order24 = (er24.groupby("category")["er_pct"].median()
               .sort_values(ascending=False).index.tolist())

fig, ax = plt.subplots(figsize=(12, 5))
sns.boxplot(data=er24, x="category", y="er_pct", hue="platform",
            order=cat_order24, palette=PALETTE,
            width=0.55, linewidth=0.8,
            flierprops=dict(marker="o", markersize=2, alpha=0.2),
            ax=ax)
ax.set_title("Engagement Rate by Content Category and Platform — 2024", fontweight="bold")
ax.set_ylabel("Engagement Rate (%)")
ax.set_xlabel("")
plt.xticks(rotation=20, ha="right", fontsize=9)
ax.legend(title="Platform", fontsize=9)
savefig("11_er_by_category_platform_2024.png")

# ── FIG 12: Country × category heatmap 2022 (top 10 countries) ───────────────
print("  Fig 12: Country × category heatmap 2022 …")
top10_countries = df22k["country"].value_counts().head(10).index.tolist()
cc22 = (
    df22k[df22k["country"].isin(top10_countries)]
    .dropna(subset=["category"])
    .groupby(["country", "category"])
    .size()
    .reset_index(name="n")
)
cc22["pct"] = cc22.groupby("country")["n"].transform(lambda x: x / x.sum() * 100)
cc_pivot = cc22.pivot_table(index="country", columns="category", values="pct", aggfunc="sum").fillna(0)

fig, ax = plt.subplots(figsize=(11, 6))
sns.heatmap(cc_pivot, annot=True, fmt=".1f", cmap="YlGnBu",
            linewidths=0.4, cbar_kws={"label": "% of country's influencers"}, ax=ax)
ax.set_title("Content Category Mix by Country — 2022 (top 10 audience countries)",
             fontweight="bold")
ax.set_xlabel("Category")
ax.set_ylabel("")
plt.xticks(rotation=20, ha="right", fontsize=9)
savefig("12_country_category_heatmap_2022.png")

print("\n✅  EDA complete.")
print(f"   Figures  → {FIGS}")
print(f"   Summaries→ {NUMS}")
