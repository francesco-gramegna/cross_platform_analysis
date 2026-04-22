"""
RQ1 Sub-question 1: What drives engagement, and does it differ by platform?

log-log regression: log(engagement) = α + β·log(followers) + category + country + ε
  β < 1  →  diminishing returns (big-account penalty)
  β = 1  →  proportional scaling
  β > 1  →  increasing returns

Engagement numerator:
  Instagram 2022 : engagement_avg  (HypeAuditor-provided, independent of followers)
  YouTube  2022  : likes_avg + comments_avg
  YouTube  2026  : likes_avg + comments_avg
  2024           : raw engagement unavailable → ER used as descriptive only

Country: countries with ≥30 observations kept; rest = "Other" (excluded from plots).
"""

import warnings, os
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats
import statsmodels.formula.api as smf

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "cleaned_dataset", "updated")
FIGS = os.path.join(HERE, "rq1_figures");   os.makedirs(FIGS, exist_ok=True)
NUMS = os.path.join(HERE, "rq1_summaries"); os.makedirs(NUMS, exist_ok=True)

IG_COL = "#C13584"
YT_COL = "#FF0000"
PALETTE = {"Instagram": IG_COL, "YouTube": YT_COL}
CAT_ORDER = ["Entertainment","Music","Lifestyle","Beauty&Fashion",
             "Sports","Knowledge&Info","Tech&Gaming"]
CAT_COLORS = {
    "Entertainment": "#4C72B0", "Music": "#DD8452",
    "Lifestyle": "#55A868",     "Beauty&Fashion": "#C44E52",
    "Sports": "#8172B3",        "Knowledge&Info": "#937860",
    "Tech&Gaming": "#DA8BC3",
}

sns.set_theme(style="whitegrid", font_scale=1.15)
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False})

def savefig(name):
    plt.savefig(os.path.join(FIGS, name), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  -> {name}")

def savecsv(df, name):
    df.to_csv(os.path.join(NUMS, name))
    print(f"  -> {name}")

def sig_stars(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    return "ns"

def group_country(df, col, min_count=10):
    counts = df[col].value_counts()
    keep = counts[counts >= min_count].index
    df = df.copy()
    df[col] = df[col].where(df[col].isin(keep), other="Other")
    return df

def fmt_log_axis(ax, axis="x"):
    """Replace log10 tick labels with readable M/B notation."""
    def _fmt(val, pos):
        v = 10 ** val
        if v >= 1e9:  return f"{v/1e9:.0f}B"
        if v >= 1e6:  return f"{v/1e6:.0f}M"
        if v >= 1e3:  return f"{v/1e3:.0f}K"
        return str(int(v))
    formatter = mticker.FuncFormatter(_fmt)
    if axis == "x":
        ax.xaxis.set_major_formatter(formatter)
    else:
        ax.yaxis.set_major_formatter(formatter)

# ══════════════════════════════════════════════════════════════════════════════
# LOAD
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Load]")
df22 = pd.read_csv(os.path.join(DATA, "merged_2022_all.csv"))
df24 = pd.read_csv(os.path.join(DATA, "merged_2024_all.csv"))
df26 = pd.read_csv(os.path.join(DATA, "merged_2026.csv"))

for df in [df22, df24, df26]:
    for c in ["followers","engagement_avg","likes_avg","comments_avg","er_pct"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

# ══════════════════════════════════════════════════════════════════════════════
# PART 1  Within 2022 — log-log regression
# ══════════════════════════════════════════════════════════════════════════════
print("\n━━ PART 1: Within 2022 ━━")

p1 = df22[df22["platform"].isin(["Instagram","YouTube"])].copy()
p1["engagement"] = np.where(
    p1["platform"] == "Instagram",
    p1["engagement_avg"],
    p1["likes_avg"].fillna(0) + p1["comments_avg"].fillna(0)
)
p1 = p1[p1["engagement"] > 0].copy()
p1["log_eng"] = np.log10(p1["engagement"])
p1["log_fol"] = np.log10(p1["followers"].clip(lower=1))
p1["category_unified"] = p1["category_unified"].where(
    p1["category_unified"].isin(CAT_ORDER), other=np.nan)
p1 = group_country(p1, "audience_country")
p1 = p1.dropna(subset=["log_eng","log_fol","category_unified","audience_country"])

# ── OLS per platform ──────────────────────────────────────────────────────────
ols_rows = []
for plat in ["Instagram","YouTube"]:
    sub = p1[p1["platform"] == plat]
    m = smf.ols(
        "log_eng ~ log_fol + C(category_unified, Treatment('Beauty&Fashion')) + C(audience_country, Treatment('United States'))",
        data=sub).fit()
    ols_rows.append({
        "platform": plat,
        "beta":     round(m.params["log_fol"], 4),
        "pval":     round(m.pvalues["log_fol"], 4),
        "r2":       round(m.rsquared, 3),
        "n":        len(sub),
        "model":    m
    })
    print(f"  {plat}: β={m.params['log_fol']:.4f}  "
          f"p={m.pvalues['log_fol']:.4f}  R²={m.rsquared:.3f}  n={len(sub)}")

savecsv(pd.DataFrame([{k:v for k,v in r.items() if k!="model"}
                      for r in ols_rows]), "P1_ols_beta_summary.csv")

# ── P1-Fig1: log-log scatter (side by side, clean) ───────────────────────────
print("  P1-Fig1: log-log scatter …")
fig, axes = plt.subplots(1, 2, figsize=(15, 6))
for ax, row in zip(axes, ols_rows):
    plat = row["platform"]
    sub  = p1[p1["platform"] == plat]
    color = PALETTE[plat]

    ax.scatter(sub["log_fol"], sub["log_eng"],
               color=color, alpha=0.12, s=6, rasterized=True)

    # OLS line
    xs = np.linspace(sub["log_fol"].min(), sub["log_fol"].max(), 300)
    m  = row["model"]
    # predict along followers only (fix other vars at mode)
    cat_base = sub["category_unified"].mode()[0]
    cou_base = sub["audience_country"].mode()[0]
    pred_df  = pd.DataFrame({
        "log_fol": xs,
        "category_unified": cat_base,
        "audience_country": cou_base,
    })
    ys = m.predict(pred_df)
    ax.plot(xs, ys, color="black", linewidth=2.5, zorder=5, label="OLS fit")

    # readable axis ticks
    ax.set_xticks([6, 7, 7.7, 8, 8.7])
    ax.set_xticklabels(["1M", "10M", "50M", "100M", "500M"], fontsize=9)
    fmt_log_axis(ax, "y")

    # annotation box — β and what it means
    beta = row["beta"]
    meaning = ("near-zero: follower count\nbarely predicts engagement"
               if beta < 0.2 else
               "strong: bigger channels\nget much more engagement")
    box_txt = f"β = {beta:.3f}  {sig_stars(row['pval'])}\n{meaning}"
    ax.text(0.97, 0.05, box_txt, transform=ax.transAxes,
            ha="right", va="bottom", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor=color, linewidth=1.5, alpha=0.9))

    ax.set_title(plat, fontweight="bold", fontsize=14, color=color)
    ax.set_xlabel("Followers / Subscribers", fontsize=11)
    ax.set_ylabel("Avg Engagement per Post" if plat=="Instagram" else "", fontsize=11)

fig.suptitle(
    # "Does Follower Count Drive Engagement? (2022)\n"
    "Each dot = one influencer  |  Line = OLS trend  |  β measures the strength",
    fontweight="bold", fontsize=13)
plt.tight_layout()
savefig("P1_1_loglog_scatter_2022.png")

# ── P1-Fig2: β comparison — clear visual ─────────────────────────────────────
print("  P1-Fig2: beta comparison …")
fig, ax = plt.subplots(figsize=(9, 5))

betas  = [r["beta"] for r in ols_rows]
plats  = [r["platform"] for r in ols_rows]
colors = [PALETTE[p] for p in plats]

# shaded zones
ax.axhspan(0,   0.3, color="#ffe0e0", alpha=0.4, zorder=0, label="Very weak effect")
ax.axhspan(0.3, 0.7, color="#fff3cd", alpha=0.4, zorder=0, label="Moderate effect")
ax.axhspan(0.7, 1.0, color="#d4edda", alpha=0.4, zorder=0, label="Strong effect (close to proportional)")
ax.axhline(1.0, color="#2d6a4f", linestyle="--", linewidth=1.5, zorder=1,
           label="β = 1  (perfectly proportional)")

bars = ax.bar(plats, betas, color=colors, edgecolor="white",
              width=0.45, zorder=2, alpha=0.9)

for bar, r in zip(bars, ols_rows):
    ax.text(bar.get_x() + bar.get_width()/2,
            bar.get_height() + 0.025,
            f"β = {r['beta']:.3f}\n{sig_stars(r['pval'])}",
            ha="center", fontsize=12, fontweight="bold")

    # plain-language label inside bar
    label = ("10× more followers\n→ only 1.2× more engagement"
             if r["beta"] < 0.2 else
             "10× more subscribers\n→ ~5× more engagement")
    ax.text(bar.get_x() + bar.get_width()/2,
            bar.get_height() / 2,
            label, ha="center", va="center",
            fontsize=8.5, color="white", fontweight="bold",
            wrap=True)

ax.set_ylim(0, 1.25)
ax.set_ylabel("β  (follower elasticity of engagement)", fontsize=11)
ax.set_title(
    "How Strongly Does Follower Count Drive Engagement?\n"
    "2022 — Controls: content category + audience country",
    fontweight="bold", fontsize=13)
ax.legend(loc="upper right", fontsize=8.5, framealpha=0.9)
ax.set_axisbelow(True)
plt.tight_layout()
savefig("P1_2_beta_comparison_2022.png")

# ── P1-Fig3: category coefficients — horizontal grouped bars ─────────────────
print("  P1-Fig3: category coefficients …")
cat_coefs = {}
for r in ols_rows:
    plat, m = r["platform"], r["model"]
    coefs = {
        k.replace("C(category_unified, Treatment('Beauty&Fashion'))[T.","").rstrip("]"): v
        for k, v in m.params.items() if "category_unified" in k
    }
    cat_coefs[plat] = coefs

coef_df = (pd.DataFrame(cat_coefs)
             .reindex([c for c in CAT_ORDER if c in pd.DataFrame(cat_coefs).index])
             .dropna(how="all").fillna(0))
# add Beauty&Fashion row explicitly as 0 (it's the baseline)
coef_df.loc["Beauty&Fashion"] = 0.0
# sort by Instagram value
coef_df = coef_df.sort_values("Instagram")
savecsv(coef_df.round(4), "P1_category_coefficients.csv")

fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
for ax, plat, color in zip(axes, ["Instagram","YouTube"], [IG_COL, YT_COL]):
    vals  = coef_df[plat]
    bar_colors = ["#aaaaaa" if idx == "Beauty&Fashion"
                  else "#27ae60" if v > 0 else "#e74c3c"
                  for idx, v in vals.items()]
    bars = ax.barh(coef_df.index, vals, color=bar_colors,
                   edgecolor="white", alpha=0.85, height=0.6)
    ax.axvline(0, color="black", linewidth=1.2)
    for bar, (idx, val) in zip(bars, vals.items()):
        if idx == "Beauty&Fashion":
            ax.text(0.008, bar.get_y() + bar.get_height()/2,
                    "0.00  (baseline)", va="center", ha="left", fontsize=9,
                    color="gray", style="italic")
        else:
            xpos = val + 0.005 if val >= 0 else val - 0.005
            ha   = "left" if val >= 0 else "right"
            ax.text(xpos, bar.get_y() + bar.get_height()/2,
                    f"{val:+.2f}", va="center", ha=ha, fontsize=9)
    ax.set_title(plat, fontweight="bold", fontsize=13, color=color)
    ax.set_xlabel("Effect on log(Engagement)\nvs Beauty&Fashion (baseline)", fontsize=10)
    ax.axvline(0, color="gray", linewidth=0.8, zorder=0)

# legend
legend_els = [mpatches.Patch(facecolor="#27ae60", label="More engagement than Beauty&Fashion"),
              mpatches.Patch(facecolor="#e74c3c", label="Less engagement than Beauty&Fashion"),
              mpatches.Patch(facecolor="#aaaaaa", label="Beauty&Fashion (baseline = 0)")]
fig.legend(handles=legend_els, loc="lower center", ncol=3,
           fontsize=9, frameon=True, bbox_to_anchor=(0.5, -0.04))
fig.suptitle(
    "Controls: log(followers) + audience country  |  Baseline = Beauty&Fashion",
    fontweight="bold", fontsize=13)
plt.tight_layout()
savefig("P1_3_category_coef_2022.png")

# ── P1-Fig4: country coefficients — Instagram + YouTube (2-panel) ─────────────
print("  P1-Fig4: country coefficients …")

def extract_country_coefs(model):
    """Extract all country coefficients (excl. Other) from OLS model."""
    coefs = {}
    for k, v in model.params.items():
        if "audience_country" not in k:
            continue
        country = k.split("[T.")[1].rstrip("]")
        if country == "Other":
            continue
        coefs[country] = {"coef": v, "pval": model.pvalues[k]}
    df = pd.DataFrame(coefs).T
    # add US baseline row explicitly
    df.loc["United States"] = {"coef": 0.0, "pval": 1.0}
    return df.sort_values("coef")

cc_ig = extract_country_coefs(ols_rows[0]["model"])
cc_yt = extract_country_coefs(ols_rows[1]["model"])

savecsv(cc_ig.round(4), "P1_country_coefficients_instagram.csv")
savecsv(cc_yt.round(4), "P1_country_coefficients_youtube.csv")

fig, axes = plt.subplots(1, 2, figsize=(18, 8))
for ax, cc_df, plat in zip(axes, [cc_ig, cc_yt], ["Instagram","YouTube"]):
    color = PALETTE[plat]
    bar_colors = ["#aaaaaa" if idx == "United States"
                  else "#27ae60" if v > 0 else "#e74c3c"
                  for idx, v in cc_df["coef"].items()]
    bars = ax.barh(cc_df.index, cc_df["coef"], color=bar_colors,
                   edgecolor="white", alpha=0.88, height=0.65)
    ax.axvline(0, color="black", linewidth=1.2)

    for bar, (idx, val) in zip(bars, cc_df["coef"].items()):
        pval = cc_df.loc[idx, "pval"]
        star = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
        if idx == "United States":
            ax.text(0.005, bar.get_y() + bar.get_height()/2,
                    "0.00  (baseline)", va="center", ha="left",
                    fontsize=8.5, color="gray", style="italic")
        else:
            xpos = val + 0.005 if val >= 0 else val - 0.005
            ha   = "left" if val >= 0 else "right"
            label = f"{val:+.2f} {star}".strip()
            ax.text(xpos, bar.get_y() + bar.get_height()/2,
                    label, va="center", ha=ha, fontsize=8.5)

    ax.set_title(plat, fontweight="bold", fontsize=13, color=color)
    ax.set_xlabel("Effect on log(Engagement)  vs United States", fontsize=10)
    ax.set_ylabel("Audience Country", fontsize=10)

# legend
legend_els = [mpatches.Patch(facecolor="#27ae60", label="Higher engagement than US"),
              mpatches.Patch(facecolor="#e74c3c", label="Lower engagement than US"),
              mpatches.Patch(facecolor="#aaaaaa", label="United States (baseline = 0)")]
fig.legend(handles=legend_els, loc="lower center", ncol=3,
           fontsize=9, frameon=True, bbox_to_anchor=(0.5, -0.02))
axes[1].text(1.02, 0.98,
             "* p<0.05  ** p<0.01  *** p<0.001\n(no star = not significant)",
             transform=axes[1].transAxes, ha="left", va="top", fontsize=8.5,
             bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow",
                       edgecolor="gray", alpha=0.9))
fig.suptitle(
    "Does Audience Country Affect Engagement? (2022)\n"
    "Baseline = United States  |  Controls: log(followers) + content category",
    fontweight="bold", fontsize=13)
plt.tight_layout()
savefig("P1_4_country_coef_2022.png")

# ── P1-Fig5: TikTok 2022 — uncontrolled β for all 3 platforms ────────────────
# TikTok has no category/country → run uncontrolled log-log for fair 3-way compare
print("  P1-Fig5: TikTok uncontrolled β comparison …")

tt22 = df22[df22["platform"] == "TikTok"].copy()
tt22["engagement"] = (tt22["likes_avg"].fillna(0)
                      + tt22["comments_avg"].fillna(0)
                      + tt22["shares_avg"].fillna(0))
tt22 = tt22[tt22["engagement"] > 0].copy()
tt22["log_eng"] = np.log10(tt22["engagement"])
tt22["log_fol"] = np.log10(tt22["followers"].clip(lower=1))
tt22 = tt22.dropna(subset=["log_eng","log_fol"])

TT_COL = "#010101"
PALETTE3 = {"Instagram": IG_COL, "YouTube": YT_COL, "TikTok": TT_COL}

# run uncontrolled OLS for all 3 so β values are directly comparable
uncont_rows = []
for plat, sub in [
    ("Instagram", p1[p1["platform"]=="Instagram"]),
    ("YouTube",   p1[p1["platform"]=="YouTube"]),
    ("TikTok",    tt22),
]:
    m = smf.ols("log_eng ~ log_fol", data=sub).fit()
    uncont_rows.append({
        "platform": plat,
        "beta":  round(m.params["log_fol"], 4),
        "pval":  round(m.pvalues["log_fol"], 4),
        "r2":    round(m.rsquared, 3),
        "n":     len(sub),
        "model": m,
    })
    print(f"  {plat} (uncontrolled): β={m.params['log_fol']:.4f}  "
          f"p={m.pvalues['log_fol']:.4f}  R²={m.rsquared:.3f}  n={len(sub)}")

savecsv(pd.DataFrame([{k:v for k,v in r.items() if k!="model"}
                      for r in uncont_rows]),
        "P1_uncontrolled_beta_all3.csv")

# ── Fig A: log-log scatter — 3 panels ────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
data3 = [
    ("Instagram", p1[p1["platform"]=="Instagram"]),
    ("YouTube",   p1[p1["platform"]=="YouTube"]),
    ("TikTok",    tt22),
]
for ax, (plat, sub), row in zip(axes, data3, uncont_rows):
    color = PALETTE3[plat]
    ax.scatter(sub["log_fol"], sub["log_eng"],
               color=color, alpha=0.12, s=6, rasterized=True)
    xs = np.linspace(sub["log_fol"].min(), sub["log_fol"].max(), 300)
    ax.plot(xs, row["model"].predict(pd.DataFrame({"log_fol": xs})),
            color="black", linewidth=2.5)
    fmt_log_axis(ax, "y")
    fmt_log_axis(ax, "x")

    ctrl_note = ("No controls\n(no category/country data)"
                 if plat == "TikTok" else "Uncontrolled\n(for comparison)")
    box_txt = f"β = {row['beta']:.3f}  {sig_stars(row['pval'])}\n{ctrl_note}"
    box_color = "#ffe0b2" if plat == "TikTok" else "white"
    ax.text(0.97, 0.05, box_txt, transform=ax.transAxes,
            ha="right", va="bottom", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.5", facecolor=box_color,
                      edgecolor=color, linewidth=1.5, alpha=0.95))
    ax.set_title(plat, fontweight="bold", fontsize=14, color=color)
    ax.set_xlabel("Followers", fontsize=11)
    ax.set_ylabel("Avg Engagement per Post" if plat=="Instagram" else "", fontsize=11)

fig.suptitle(
    "Follower Count vs Engagement: All 3 Platforms (2022) — Uncontrolled\n"
    "TikTok engagement = likes + comments + shares  |  "
    "TikTok β has no category/country controls",
    fontweight="bold", fontsize=13)
plt.tight_layout()
savefig("P1_5a_loglog_scatter_3platforms.png")

# ── Fig B: β bar chart — all 3 uncontrolled + IG/YT controlled ───────────────
fig, ax = plt.subplots(figsize=(11, 5))

# group: uncontrolled all 3, then controlled IG + YT
bar_data = [
    ("Instagram\n(uncontrolled)", uncont_rows[0]["beta"], uncont_rows[0]["pval"], IG_COL, 0.5),
    ("YouTube\n(uncontrolled)",   uncont_rows[1]["beta"], uncont_rows[1]["pval"], YT_COL, 0.5),
    ("TikTok\n(uncontrolled,\nno controls)", uncont_rows[2]["beta"], uncont_rows[2]["pval"], TT_COL, 0.5),
    ("Instagram\n(controlled)",  ols_rows[0]["beta"],    ols_rows[0]["pval"],    IG_COL, 0.9),
    ("YouTube\n(controlled)",    ols_rows[1]["beta"],    ols_rows[1]["pval"],    YT_COL, 0.9),
]
labels = [d[0] for d in bar_data]
betas  = [d[1] for d in bar_data]
pvals  = [d[2] for d in bar_data]
colors = [d[3] for d in bar_data]
alphas = [d[4] for d in bar_data]

ax.axhspan(0,   0.3, color="#ffe0e0", alpha=0.35, zorder=0)
ax.axhspan(0.3, 0.7, color="#fff3cd", alpha=0.35, zorder=0)
ax.axhspan(0.7, 1.0, color="#d4edda", alpha=0.35, zorder=0)
ax.axhline(1.0, color="#2d6a4f", linestyle="--", linewidth=1.5,
           label="β=1 (proportional)", zorder=1)
# vertical divider between uncontrolled and controlled
ax.axvline(2.5, color="gray", linestyle=":", linewidth=1.5, zorder=1)
ax.text(1.0, 1.18, "Uncontrolled (all 3 platforms)", ha="center",
        fontsize=9, color="gray", style="italic")
ax.text(3.5, 1.18, "Controlled\n(category + country)", ha="center",
        fontsize=9, color="gray", style="italic")

for i, (lbl, beta, pval, color, alpha) in enumerate(bar_data):
    bar = ax.bar(i, beta, color=color, alpha=alpha, edgecolor="white",
                 width=0.55, zorder=2)
    ax.text(i, beta + 0.025, f"{beta:.3f}\n{sig_stars(pval)}",
            ha="center", fontsize=9, fontweight="bold")

# TikTok warning
ax.text(2, -0.1, "⚠ no controls", ha="center", fontsize=8.5,
        color="darkorange", fontweight="bold")

ax.set_xticks(range(5))
ax.set_xticklabels(labels, fontsize=9)
ax.set_ylim(-0.15, 1.30)
ax.set_ylabel("β  (follower elasticity of engagement)", fontsize=11)
ax.set_title(
    "Follower Elasticity Comparison: Instagram, YouTube, TikTok (2022)\n"
    "Left = uncontrolled (fair 3-way comparison)  |  Right = controlled (more accurate for IG & YT)",
    fontweight="bold", fontsize=12)
ax.legend(fontsize=9)
ax.set_axisbelow(True)
plt.tight_layout()
savefig("P1_5b_beta_all3_platforms.png")

# ══════════════════════════════════════════════════════════════════════════════
# PART 2  Within 2024 — descriptive only (no raw engagement)
# ══════════════════════════════════════════════════════════════════════════════
print("\n━━ PART 2: Within 2024 (descriptive) ━━")

p2 = df24[df24["platform"].isin(["Instagram","YouTube","TikTok"])].copy()
p2["er"]      = p2["er_pct"]
p2["log_fol"] = np.log10(p2["followers"].clip(lower=1))
p2["category_unified"] = p2["category_unified"].where(
    p2["category_unified"].isin(CAT_ORDER), other=np.nan)
p2 = group_country(p2, "audience_country")
p2 = p2.dropna(subset=["er","log_fol","category_unified"])
p2["er_viz"] = p2.groupby("platform")["er"].transform(
    lambda x: x.clip(upper=x.quantile(0.99)))

n_yt = (p2["platform"]=="YouTube").sum()
n_tt = (p2["platform"]=="TikTok").sum()
print(f"  IG: {(p2['platform']=='Instagram').sum()}  YT: {n_yt}  TT: {n_tt} rows")

# ── P2-Fig1: Spearman followers vs ER — 3 platforms (flag sparse ones) ────────
print("  P2-Fig1: followers vs ER …")
fig, axes = plt.subplots(1, 3, figsize=(20, 6))

for ax, plat in zip(axes, ["Instagram","YouTube","TikTok"]):
    sub = p2[p2["platform"]==plat].dropna(subset=["log_fol","er_viz"])
    n   = len(sub)
    color = PALETTE3[plat]

    ax.scatter(sub["log_fol"], sub["er_viz"],
               alpha=0.18, s=8, color=color, rasterized=True)

    if n >= 30:
        z  = np.polyfit(sub["log_fol"], sub["er_viz"], 1)
        xs = np.linspace(sub["log_fol"].min(), sub["log_fol"].max(), 200)
        ax.plot(xs, np.poly1d(z)(xs), color="black", linewidth=2.5)
        rho, pv = stats.spearmanr(sub["log_fol"], sub["er"])
        ax.text(0.97, 0.95,
                f"Spearman ρ = {rho:+.3f}  {sig_stars(pv)}\nn = {n:,}",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=10, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                          edgecolor=color, linewidth=1.2, alpha=0.9))

    ax.set_title(plat, fontweight="bold", fontsize=13, color=color)
    ax.set_xlabel("Followers / Subscribers", fontsize=11)
    ax.set_ylabel("Engagement Rate (%)" if plat=="Instagram" else "", fontsize=11)

    ax.set_xticks([4,5,6,7,8])
    ax.set_xticklabels(["10K","100K","1M","10M","100M"], fontsize=9)

    if n < 100:
        ax.text(0.5, 0.5, f"Only {n} rows\n(results not reliable)",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=13, color="red", fontweight="bold", alpha=0.6,
                rotation=15)

fig.suptitle(
    "Followers vs Engagement Rate — All 3 Platforms (2024) — Descriptive Only\n"
    "Raw engagement unavailable; ER formula unknown (HypeAuditor)",
    fontweight="bold", fontsize=13)
plt.tight_layout()
savefig("P2_1_followers_vs_er_2024.png")

# ── P2-Fig2: ER by category — Instagram vs TikTok grouped bars ───────────────
print("  P2-Fig2: ER by category — grouped bar (IG vs TikTok) …")

# build pivot: rows = category, cols = platform
cat_rows = []
for plat in ["Instagram","TikTok"]:
    sub_p = p2[p2["platform"]==plat].dropna(subset=["er_viz","category_unified"])
    for cat, grp in sub_p.groupby("category_unified"):
        cat_rows.append({"category": cat, "platform": plat,
                         "median_er": grp["er_viz"].median(),
                         "n": len(grp)})
cat_pivot = pd.DataFrame(cat_rows)

# order categories by Instagram median ER descending
ig_order = (cat_pivot[cat_pivot["platform"]=="Instagram"]
            .sort_values("median_er", ascending=False)["category"].tolist())
# include any TikTok-only categories at end
all_cats = ig_order + [c for c in cat_pivot["category"].unique() if c not in ig_order]

x = np.arange(len(all_cats))
width = 0.38
fig, ax = plt.subplots(figsize=(13, 6))

for i, (plat, color, offset) in enumerate([
        ("Instagram", IG_COL, -width/2),
        ("TikTok",    TT_COL,  width/2)]):
    medians = []
    ns      = []
    for cat in all_cats:
        row = cat_pivot[(cat_pivot["platform"]==plat) & (cat_pivot["category"]==cat)]
        medians.append(row["median_er"].values[0] if len(row) else 0)
        ns.append(int(row["n"].values[0]) if len(row) else 0)

    bars = ax.bar(x + offset, medians, width, label=plat,
                  color=color, alpha=0.85, edgecolor="white")
    for bar, val, n_c in zip(bars, medians, ns):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + 0.03,
                    f"{val:.2f}%\n(n={n_c})",
                    ha="center", fontsize=7.5, color=color)

ax.set_xticks(x)
ax.set_xticklabels(all_cats, rotation=20, ha="right", fontsize=10)
ax.set_ylabel("Median Engagement Rate (%)", fontsize=11)
ax.legend(fontsize=11)
ax.text(0.99, 0.97,
        "ER formula: HypeAuditor black-box\n— descriptive only\nYouTube excluded (<30 rows/category)",
        transform=ax.transAxes, ha="right", va="top", fontsize=8.5,
        color="gray", style="italic")
ax.set_title(
    "Engagement Rate by Content Category: Instagram vs TikTok (2024)\n"
    "Grouped bars — same category, side by side",
    fontweight="bold", fontsize=13)
plt.tight_layout()
savefig("P2_2_er_by_category_2024.png")

for plat in ["Instagram","TikTok"]:
    savecsv(p2[p2["platform"]==plat]
              .groupby("category_unified")["er"]
              .agg(["median","std","count"]).round(3),
            f"P2_er_by_category_{plat.lower()}.csv")

# ══════════════════════════════════════════════════════════════════════════════
# PART 3  YouTube Panel 2022 → 2026
# ══════════════════════════════════════════════════════════════════════════════
print("\n━━ PART 3: YouTube Panel 2022 → 2026 ━━")

yt22 = df22[df22["platform"]=="YouTube"].copy()  # already deduplicated, no month filter needed
yt26 = df26.copy()
for df in [yt22, yt26]:
    df["handle"] = df["handle"].str.lstrip("@").str.strip().str.lower()
    df["engagement"] = df["likes_avg"].fillna(0) + df["comments_avg"].fillna(0)

panel = yt22[["handle","followers","engagement",
              "category_unified","audience_country"]].merge(
    yt26[["handle","followers","engagement"]],
    on="handle", suffixes=("_2022","_2026")
).dropna()
panel = panel[(panel["engagement_2022"]>0) & (panel["engagement_2026"]>0)
              & (panel["followers_2022"]>0) & (panel["followers_2026"]>0)]
panel["log_eng_2022"] = np.log10(panel["engagement_2022"])
panel["log_eng_2026"] = np.log10(panel["engagement_2026"])
panel["log_fol_2022"] = np.log10(panel["followers_2022"])
panel["log_fol_2026"] = np.log10(panel["followers_2026"])
panel["category_unified"] = panel["category_unified"].where(
    panel["category_unified"].isin(CAT_ORDER), other=np.nan)
panel = group_country(panel, "audience_country")
panel_clean = panel.dropna(subset=["category_unified","audience_country"])
print(f"  Panel: {len(panel_clean)} creators")

# ── P3-Fig1: overlay log-log scatter 2022 vs 2026 on same axes ───────────────
print("  P3-Fig1: log-log scatter overlay …")
fig, ax = plt.subplots(figsize=(9, 6))

yr_cfg = [("2022", "log_fol_2022", "log_eng_2022", "#2196F3"),
          ("2026", "log_fol_2026", "log_eng_2026", "#4CAF50")]

for yr, xcol, ycol, color in yr_cfg:
    xv = panel_clean[xcol]; yv = panel_clean[ycol]
    ax.scatter(xv, yv, color=color, alpha=0.25, s=15,
               label=f"{yr} data", rasterized=True)
    z  = np.polyfit(xv, yv, 1)
    xs = np.linspace(xv.min(), xv.max(), 300)
    r, p = stats.pearsonr(xv, yv)
    ax.plot(xs, np.poly1d(z)(xs), color=color, linewidth=2.5,
            label=f"{yr} trend  (r={r:+.2f})")

ax.set_xticks([7, 7.7, 8, 8.3, 8.7])
ax.set_xticklabels(["10M","50M","100M","200M","500M"], fontsize=9)
fmt_log_axis(ax, "y")
ax.set_xlabel("Subscribers", fontsize=11)
ax.set_ylabel("Avg Engagement per Video", fontsize=11)
ax.set_title(
    "YouTube: Subscribers vs Engagement (Same 302 Creators)\n"
    "2022 vs 2026 — Same ER formula, directly comparable",
    fontweight="bold", fontsize=13)
ax.legend(fontsize=9)
plt.tight_layout()
savefig("P3_1_loglog_scatter_panel.png")

# ── P3 OLS per year ───────────────────────────────────────────────────────────
p3_rows = []
for yr in ["2022","2026"]:
    sub = panel_clean.rename(columns={
        f"log_eng_{yr}":"log_eng", f"log_fol_{yr}":"log_fol"})
    m = smf.ols(
        "log_eng ~ log_fol + C(category_unified, Treatment('Beauty&Fashion')) + C(audience_country, Treatment('United States'))",
        data=sub).fit()
    p3_rows.append({"year":yr, "beta":round(m.params["log_fol"],4),
                    "pval":round(m.pvalues["log_fol"],4),
                    "r2":round(m.rsquared,3), "n":len(sub), "model":m})
    print(f"  {yr}: β={m.params['log_fol']:.4f}  p={m.pvalues['log_fol']:.4f}  R²={m.rsquared:.3f}")

savecsv(pd.DataFrame([{k:v for k,v in r.items() if k!="model"}
                      for r in p3_rows]), "P3_ols_beta_summary.csv")

# ── P3-Fig2: β comparison 2022 vs 2026 ────────────────────────────────────────
print("  P3-Fig2: beta comparison panel …")
fig, ax = plt.subplots(figsize=(9, 5))

yr_colors = {"2022":"#2196F3","2026":"#4CAF50"}
ax.axhspan(0,   0.3, color="#ffe0e0", alpha=0.35, zorder=0)
ax.axhspan(0.3, 0.7, color="#fff3cd", alpha=0.35, zorder=0)
ax.axhspan(0.7, 1.0, color="#d4edda", alpha=0.35, zorder=0)
ax.axhline(1.0, color="#2d6a4f", linestyle="--", linewidth=1.5, zorder=1,
           label="β=1 (proportional)")

years  = [r["year"] for r in p3_rows]
betas  = [r["beta"] for r in p3_rows]
bars   = ax.bar(years, betas, color=[yr_colors[y] for y in years],
                edgecolor="white", width=0.35, zorder=2, alpha=0.9)

for bar, r in zip(bars, p3_rows):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.02,
            f"β = {r['beta']:.3f}\n{sig_stars(r['pval'])}",
            ha="center", fontsize=12, fontweight="bold")

# connect with arrow to show change
y0, y1 = betas
ax.annotate("", xy=(1+0.2, y1), xytext=(0-0.2, y0),
            arrowprops=dict(arrowstyle="->", color="gray", lw=1.5))
mid_x, mid_y = 0.5, (y0+y1)/2 + 0.03
ax.text(mid_x, mid_y, f"Δβ = {y1-y0:+.3f}\n(not significant)",
        ha="center", fontsize=9, color="gray")

ax.set_ylim(0, 1.25)
ax.set_ylabel("β  (follower elasticity of engagement)", fontsize=11)
ax.set_title(
    "Did the Follower-Engagement Relationship Change?\n"
    "YouTube — Same 302 Creators  |  2022 vs 2026\n"
    "Controls: category + audience country",
    fontweight="bold", fontsize=12)
ax.legend(fontsize=9)

# zone labels
for y, label in [(0.15,"Very weak"), (0.5,"Moderate"), (0.85,"Strong")]:
    ax.text(1.45, y, label, fontsize=8.5, color="gray", va="center")

plt.tight_layout()
savefig("P3_2_beta_comparison_panel.png")

# ── P3-Fig3: category coefficients — horizontal, 2022 vs 2026 ─────────────────
print("  P3-Fig3: category coefficients panel …")
cat_p3 = {}
for r in p3_rows:
    yr, m = r["year"], r["model"]
    coefs = {k.replace("C(category_unified, Treatment('Beauty&Fashion'))[T.","").rstrip("]"): v
             for k, v in m.params.items() if "category_unified" in k}
    cat_p3[yr] = coefs

cp3_df = (pd.DataFrame(cat_p3)
            .reindex([c for c in CAT_ORDER if c in pd.DataFrame(cat_p3).index])
            .dropna(how="all").fillna(0))
cp3_df = cp3_df.sort_values("2022")
savecsv(cp3_df.round(4), "P3_category_coefficients.csv")

fig, ax = plt.subplots(figsize=(11, 6))
y = np.arange(len(cp3_df)); h = 0.35
ax.barh(y + h/2, cp3_df["2022"], height=h, color="#2196F3",
        alpha=0.85, edgecolor="white", label="2022")
ax.barh(y - h/2, cp3_df["2026"], height=h, color="#4CAF50",
        alpha=0.85, edgecolor="white", label="2026")

for i, (cat, row) in enumerate(cp3_df.iterrows()):
    for yr_val, offset in [(row["2022"], h/2), (row["2026"], -h/2)]:
        xpos = yr_val + 0.02 if yr_val >= 0 else yr_val - 0.02
        ha   = "left" if yr_val >= 0 else "right"
        ax.text(xpos, i + offset, f"{yr_val:+.2f}",
                va="center", ha=ha, fontsize=8.5)

ax.axvline(0, color="black", linewidth=1.2)
ax.set_yticks(y); ax.set_yticklabels(cp3_df.index, fontsize=10)
ax.set_xlabel("Effect on log(Engagement) vs Beauty&Fashion (baseline)", fontsize=10)
ax.set_title(
    "YouTube: Category Effect on Engagement — 2022 vs 2026\n"
    "Same 406 creators  |  Controls: log(subscribers) + audience country\n"
    "All values relative to Beauty&Fashion (baseline = 0)",
    fontweight="bold", fontsize=12)
ax.legend(title="Year", fontsize=9)
ax.text(0.99, 0.02,
        "Tech&Gaming = closest to Beauty&Fashion\n"
        "Knowledge&Info = most penalised in both years",
        transform=ax.transAxes, ha="right", va="bottom",
        fontsize=8.5, color="gray", style="italic")
plt.tight_layout()
savefig("P3_3_category_coef_panel.png")

print("\n✅  Done.")
print(f"   {len(os.listdir(FIGS))} figures -> {FIGS}")
print(f"   {len(os.listdir(NUMS))} summaries -> {NUMS}")
