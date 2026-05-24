"""
Step 7: RQ1 — What features drive engagement rate?

Focus: 2022 cohort only (the methodologically uniform global top-1,000 sample).
Rationale: 2024 has 1-decimal source rounding and 25-38% non-response on TT/YT;
2024 IG country is leaderboard not audience; 2026 is a partial follow-up scrape
of YT only (~45% failed). The 2022 snapshot is the only slice family where all
three platforms are comparably measured.

Methods applied:
  - Pearson correlation                 (followers ↔ ER, per platform)
  - One-way ANOVA + η²                  (category effect on ER, per platform)
  - Multiple OLS regression             (platform-specific full model)
  - Pooled OLS with platform interaction (test if followers slope differs)
  - Residual diagnostics                (QQ + residual-vs-fitted)
  - Welch's t-test                      (cross-platform pairwise comparison)

Input:  4 - ER unified/finalData_with_er.csv
Output: 7 - statistical analysis/{plots, tables, summary.txt}
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[2]
SRC  = ROOT / "4 - ER unified" / "finalData_with_er.csv"
OUT  = ROOT / "7 - statistical analysis"
PLOT = OUT / "plots"
TBL  = OUT / "tables"
PLOT.mkdir(exist_ok=True, parents=True)
TBL.mkdir(exist_ok=True, parents=True)

PLATFORM_COLOR = {"instagram": "#E4405F", "tiktok": "#000000", "youtube": "#FF0000"}
PLATFORMS_ALL  = ["instagram", "tiktok", "youtube"]   # bivariate use
PLATFORMS_FULL = ["instagram", "youtube"]             # has category + country
BASE_CATEGORY  = "Entertainment"
BASE_COUNTRY   = "United States"
TOP_K_COUNTRIES = 15
EXCLUDE_CATEGORIES = {"Other", "UNMAPPED"}

summary = []
def log(msg=""):
    print(msg); summary.append(str(msg))

# ---------- PNG table helper ------------------------------------------------
def save_table_png(df, path, title=None, fmt=None):
    d = df.copy()
    if fmt is not None:
        for col, f in fmt.items():
            if col in d.columns:
                d[col] = d[col].map(lambda v: f(v) if pd.notna(v) else "")
    else:
        for col in d.select_dtypes("number").columns:
            d[col] = d[col].map(lambda v: f"{v:.3f}" if pd.notna(v) else "")
    if not isinstance(d.index, pd.RangeIndex):
        d = d.reset_index()
    n_rows, n_cols = d.shape
    fig_w = max(8, 1.3 * n_cols); fig_h = 0.6 + 0.38 * (n_rows + 1) + (0.4 if title else 0)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    if title:
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold", pad=10)
    tbl = ax.table(cellText=d.astype(str).values, colLabels=d.columns.astype(str).tolist(),
                   loc="center", cellLoc="center", colLoc="center")
    tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1, 1.25)
    for j in range(n_cols):
        c = tbl[0, j]; c.set_facecolor("#37474F"); c.set_text_props(color="white", fontweight="bold")
    for i in range(1, n_rows + 1):
        for j in range(n_cols):
            if i % 2 == 0:
                tbl[i, j].set_facecolor("#F4F6F7")
    fig.tight_layout(); fig.savefig(path, dpi=160, bbox_inches="tight"); plt.close(fig)

# ---------- Load + restrict to 2022, dedup per handle -----------------------
df_all = pd.read_csv(SRC, low_memory=False)
df22 = df_all[(df_all["_year"] == 2022)
              & df_all["er_pct"].notna() & (df_all["er_pct"] > 0)
              & df_all["followers"].notna() & (df_all["followers"] > 0)].copy()
log(f"Loaded {len(df_all):,} total rows; {len(df22):,} valid 2022 rows.")

def slice_data(plat, require_cat=False, require_country=False):
    s = df22[df22["_platform"] == plat].copy()
    if require_cat:
        s = s[s["category_unified"].notna()
              & ~s["category_unified"].isin(EXCLUDE_CATEGORIES)]
    if require_country:
        s = s[s["country"].notna()]
        top_c = s["country"].value_counts().head(TOP_K_COUNTRIES).index
        s = s[s["country"].isin(top_c)]
    if len(s) == 0: return s
    agg = (s.groupby("handle")
             .agg(er_pct=("er_pct", "median"),
                  followers=("followers", "median"),
                  category_unified=("category_unified", "first"),
                  country=("country", "first"))
             .reset_index())
    agg["log_er"] = np.log10(agg["er_pct"])
    agg["log_followers"] = np.log10(agg["followers"])
    agg["_platform"] = plat
    return agg

# ==========================================================================
# 1. Pearson correlation: followers ↔ ER, all 3 platforms
# ==========================================================================
log("\n" + "=" * 70 + "\n1. PEARSON CORRELATION (followers ↔ ER), per platform\n" + "=" * 70)
corr_rows = []
for plat in PLATFORMS_ALL:
    s = slice_data(plat)
    r, p = stats.pearsonr(s["log_followers"], s["log_er"])
    corr_rows.append({"platform": plat.capitalize(), "n_accounts": len(s),
                      "pearson_r": r, "p_value": p})
    log(f"  {plat.capitalize()}: n={len(s):>5}  r={r:+.3f}  p={p:.2e}")
save_table_png(pd.DataFrame(corr_rows), TBL / "T1_pearson.png",
    title="Table 1. Pearson correlation: log(followers) ↔ log(er_pct), 2022",
    fmt={"platform": str, "n_accounts": lambda v: f"{int(v):,}",
         "pearson_r": lambda v: f"{v:+.3f}", "p_value": lambda v: f"{v:.2e}"})

# ==========================================================================
# 2. One-way ANOVA: log_er ~ category, IG and YT (TikTok has no category)
# ==========================================================================
log("\n" + "=" * 70 + "\n2. ONE-WAY ANOVA on category, per platform\n" + "=" * 70)
anova_rows = []
for plat in PLATFORMS_FULL:
    s = slice_data(plat, require_cat=True)
    groups = [g["log_er"].values for _, g in s.groupby("category_unified") if len(g) >= 5]
    F, p = stats.f_oneway(*groups)
    grand = np.concatenate(groups).mean()
    ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
    ss_total   = ((np.concatenate(groups) - grand) ** 2).sum()
    eta2 = ss_between / ss_total
    anova_rows.append({"platform": plat.capitalize(), "k_groups": len(groups),
                       "n_accounts": sum(len(g) for g in groups),
                       "F": F, "p_value": p, "eta_squared": eta2})
    log(f"  {plat.capitalize()}: k={len(groups)} cats, F={F:.2f}, p={p:.2e}, η²={eta2:.3f}")
save_table_png(pd.DataFrame(anova_rows), TBL / "T2_anova.png",
    title="Table 2. One-way ANOVA of log(er_pct) across content category, 2022",
    fmt={"platform": str, "k_groups": int,
         "n_accounts": lambda v: f"{int(v):,}", "F": lambda v: f"{v:.2f}",
         "p_value": lambda v: f"{v:.2e}", "eta_squared": lambda v: f"{v:.3f}"})

# ==========================================================================
# 3. Per-platform OLS: full controlled model for IG and YT
# ==========================================================================
log("\n" + "=" * 70 + "\n3. PER-PLATFORM MULTIPLE OLS (controlled)\n" + "=" * 70)
ols_fits = {}
for plat in PLATFORMS_FULL:
    s = slice_data(plat, require_cat=True, require_country=True)
    formula = (f'log_er ~ log_followers '
               f'+ C(category_unified, Treatment(reference="{BASE_CATEGORY}")) '
               f'+ C(country, Treatment(reference="{BASE_COUNTRY}"))')
    fit = smf.ols(formula, data=s).fit()
    ols_fits[plat] = (s, fit)
    log(f"\n  {plat.capitalize()}: n={len(s):,}, R²={fit.rsquared:.3f}, "
        f"adj.R²={fit.rsquared_adj:.3f}")
    pretty = pd.DataFrame({"coef": fit.params, "std_err": fit.bse,
                           "p": fit.pvalues,
                           "ci_lo": fit.conf_int()[0],
                           "ci_hi": fit.conf_int()[1]})
    pretty.index = [t.replace('C(category_unified, Treatment(reference="Entertainment"))', "category")
                     .replace('C(country, Treatment(reference="United States"))', "country")
                     .replace("[T.", "[").rstrip("]") + "]"
                    if "[T." in t else t for t in pretty.index]
    save_table_png(pretty, TBL / f"T3_ols_{plat}.png",
        title=f"Table 3. OLS — {plat.capitalize()} 2022 "
              f"(n={len(s):,}, R²={fit.rsquared:.3f}, adj.R²={fit.rsquared_adj:.3f})",
        fmt={"coef": lambda v: f"{v:+.3f}", "std_err": lambda v: f"{v:.3f}",
             "p": lambda v: f"{v:.3g}",
             "ci_lo": lambda v: f"{v:+.3f}", "ci_hi": lambda v: f"{v:+.3f}"})

# ==========================================================================
# 4. Pooled OLS with platform × log_followers interaction
#    Tests: does the followers→ER relationship differ between IG and YT?
# ==========================================================================
log("\n" + "=" * 70 + "\n4. POOLED OLS with platform × log_followers interaction\n" + "=" * 70)
pooled = pd.concat([slice_data(p, require_cat=True, require_country=True) for p in PLATFORMS_FULL],
                   ignore_index=True)
pooled_fit = smf.ols(
    'log_er ~ log_followers * C(_platform, Treatment(reference="instagram")) '
    f'+ C(category_unified, Treatment(reference="{BASE_CATEGORY}")) '
    f'+ C(country, Treatment(reference="{BASE_COUNTRY}"))',
    data=pooled).fit()
log(f"  Pooled n={len(pooled):,}, R²={pooled_fit.rsquared:.3f}, "
    f"adj.R²={pooled_fit.rsquared_adj:.3f}")
# Pull the interaction term
interaction_terms = [t for t in pooled_fit.params.index
                     if "log_followers:" in t or ":log_followers" in t]
log("\n  Interaction term (followers slope difference vs Instagram):")
for t in interaction_terms:
    log(f"    {t}: β={pooled_fit.params[t]:+.3f}, "
        f"p={pooled_fit.pvalues[t]:.4f}")

# Headline coefficients table for slide
key_terms = ["log_followers"] + interaction_terms
pooled_key = pd.DataFrame({
    "term": [t.replace('C(_platform, Treatment(reference="instagram"))', "platform")
              .replace("[T.", "[").rstrip("]") + "]" if "[T." in t else t
             for t in key_terms],
    "coef": pooled_fit.params[key_terms].values,
    "std_err": pooled_fit.bse[key_terms].values,
    "p": pooled_fit.pvalues[key_terms].values,
})
save_table_png(pooled_key, TBL / "T4_pooled_interaction.png",
    title=f"Table 4. Pooled OLS — followers × platform interaction "
          f"(n={len(pooled):,}, adj.R²={pooled_fit.rsquared_adj:.3f})",
    fmt={"term": str, "coef": lambda v: f"{v:+.3f}",
         "std_err": lambda v: f"{v:.3f}", "p": lambda v: f"{v:.3g}"})

# Per-platform follower slope (from per-platform OLS) for visual comparison
beta_table = []
for plat in PLATFORMS_FULL:
    s, fit = ols_fits[plat]
    b  = fit.params["log_followers"]; se = fit.bse["log_followers"]
    beta_table.append({"platform": plat.capitalize(), "beta": b,
                       "se": se, "p": fit.pvalues["log_followers"]})

# ==========================================================================
# F1. Followers slope by platform (with 95% CI)
# ==========================================================================
fig, ax = plt.subplots(figsize=(6.5, 4))
xs = np.arange(len(beta_table))
betas = [r["beta"] for r in beta_table]
errs  = [1.96 * r["se"] for r in beta_table]
colors = [PLATFORM_COLOR[p.lower()] for p in [r["platform"] for r in beta_table]]
ax.bar(xs, betas, yerr=errs, capsize=5, color=colors, alpha=0.78, edgecolor="white")
for i, r in enumerate(beta_table):
    ax.text(i, r["beta"] - 0.04, f"β={r['beta']:+.2f}\np={r['p']:.1e}",
            ha="center", va="top", fontsize=9)
ax.set_xticks(xs); ax.set_xticklabels([r["platform"] for r in beta_table])
ax.axhline(0, color="gray", lw=0.6, ls=":")
ax.set_ylabel("β  for  log10(followers)")
ax.set_title("Effect of audience size on engagement rate, 2022")
fig.tight_layout(); fig.savefig(PLOT / "F1_followers_beta.png", dpi=160); plt.close(fig)

# ==========================================================================
# F2. Category coefficient forest plot, IG and YT side-by-side
# ==========================================================================
fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharex=True)
for ax, plat in zip(axes, PLATFORMS_FULL):
    s, fit = ols_fits[plat]
    terms = [p for p in fit.params.index if "category_unified" in p]
    coefs = fit.params[terms]; ci = fit.conf_int().loc[terms]
    order = coefs.sort_values().index
    coefs, ci = coefs.loc[order], ci.loc[order]
    labels = [t.split('T.')[-1].rstrip(']') for t in order]
    y = np.arange(len(coefs))
    ax.errorbar(coefs.values, y,
                xerr=[coefs.values - ci[0].values, ci[1].values - coefs.values],
                fmt="o", color=PLATFORM_COLOR[plat], capsize=3)
    ax.axvline(0, color="gray", lw=0.5, ls=":")
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.set_xlabel(f"Δ log10(er_pct) vs {BASE_CATEGORY}")
    ax.set_title(f"{plat.capitalize()} 2022  (R²={fit.rsquared:.2f})")
fig.suptitle("Category effects (OLS, 95% CI), 2022", y=1.00)
fig.tight_layout(); fig.savefig(PLOT / "F2_category_coefs.png", dpi=160); plt.close(fig)

# ==========================================================================
# F3. Country coefficient forest plot, IG and YT side-by-side
# ==========================================================================
fig, axes = plt.subplots(1, 2, figsize=(13, 7), sharex=True)
for ax, plat in zip(axes, PLATFORMS_FULL):
    s, fit = ols_fits[plat]
    terms = [p for p in fit.params.index if "country" in p]
    coefs = fit.params[terms]; ci = fit.conf_int().loc[terms]
    order = coefs.sort_values().index
    coefs, ci = coefs.loc[order], ci.loc[order]
    labels = [t.split('T.')[-1].rstrip(']') for t in order]
    y = np.arange(len(coefs))
    ax.errorbar(coefs.values, y,
                xerr=[coefs.values - ci[0].values, ci[1].values - coefs.values],
                fmt="o", color=PLATFORM_COLOR[plat], capsize=3)
    ax.axvline(0, color="gray", lw=0.5, ls=":")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel(f"Δ log10(er_pct) vs {BASE_COUNTRY}")
    ax.set_title(f"{plat.capitalize()} 2022")
fig.suptitle("Audience country effects (OLS, 95% CI), 2022", y=1.00)
fig.tight_layout(); fig.savefig(PLOT / "F3_country_coefs.png", dpi=160); plt.close(fig)

# ==========================================================================
# 5. Welch's t-test: pairwise platform comparison of ER, 2022
# ==========================================================================
log("\n" + "=" * 70 + "\n5. WELCH'S t-TEST: pairwise platform comparison (2022)\n" + "=" * 70)
sl_by_plat = {p: slice_data(p) for p in PLATFORMS_ALL}
pairs = [("instagram", "tiktok"), ("instagram", "youtube"), ("tiktok", "youtube")]
ttest_rows = []
for p1, p2 in pairs:
    a, b = sl_by_plat[p1]["log_er"], sl_by_plat[p2]["log_er"]
    t, pval = stats.ttest_ind(a, b, equal_var=False)
    ma, mb = 10**a.median(), 10**b.median()
    ttest_rows.append({"comparison": f"{p1.capitalize()} vs {p2.capitalize()}",
                       "n_a": len(a), "n_b": len(b),
                       "median_er_a": ma, "median_er_b": mb,
                       "t": t, "p_value": pval})
    log(f"  {p1.capitalize()} vs {p2.capitalize()}: "
        f"t={t:+.2f}, p={pval:.2e}, medians {ma:.2f}% vs {mb:.2f}%")
save_table_png(pd.DataFrame(ttest_rows), TBL / "T5_pairwise_ttest_platforms.png",
    title="Table 5. Welch's t-test — pairwise platform comparison of log(er_pct), 2022",
    fmt={"comparison": str, "n_a": int, "n_b": int,
         "median_er_a": lambda v: f"{v:.2f}%", "median_er_b": lambda v: f"{v:.2f}%",
         "t": lambda v: f"{v:+.2f}", "p_value": lambda v: f"{v:.2e}"})

# ==========================================================================
# 6. YouTube 2022 → 2026 longitudinal paired analysis
#    YT 2026 = follow-up scrape of YT 2022 top-1000 cohort (998 handles overlap
#    after @-prefix normalization).
# ==========================================================================
log("\n" + "=" * 70 + "\n6. YT 2022 → 2026 LONGITUDINAL ANALYSIS (paired t-test)\n" + "=" * 70)

def norm_handle(s):
    return s.dropna().astype(str).str.lower().str.strip().str.lstrip("@")

yt22_raw = df_all[(df_all["_platform"] == "youtube") & (df_all["_year"] == 2022)].copy()
yt26_raw = df_all[(df_all["_platform"] == "youtube") & (df_all["_year"] == 2026)].copy()
yt22_raw["_handle_norm"] = norm_handle(yt22_raw["handle"])
yt26_raw["_handle_norm"] = norm_handle(yt26_raw["handle"])

# YT 2022 top-1000 cohort size (unique handles)
cohort_2022 = set(yt22_raw["_handle_norm"].dropna())
# Successfully re-scraped in 2026: any YT 2026 row with at least followers or ER
scraped_2026 = set(yt26_raw[yt26_raw["er_pct"].notna() | yt26_raw["followers"].notna()]
                   ["_handle_norm"].dropna())
attrition_rate = 1 - len(scraped_2026 & cohort_2022) / len(cohort_2022)
log(f"  YT 2022 cohort (unique handles): {len(cohort_2022):,}")
log(f"  Successfully re-scraped in 2026: {len(scraped_2026 & cohort_2022):,}")
log(f"  Attrition rate (no usable 2026 data): {attrition_rate*100:.1f}%")

# Paired comparison on survivors (both periods have ER > 0)
yt22_per = (yt22_raw[yt22_raw["er_pct"].notna() & (yt22_raw["er_pct"] > 0)]
            .groupby("_handle_norm")["er_pct"].median().rename("er_2022"))
yt26_per = (yt26_raw[yt26_raw["er_pct"].notna() & (yt26_raw["er_pct"] > 0)]
            .groupby("_handle_norm")["er_pct"].median().rename("er_2026"))
paired = pd.concat([yt22_per, yt26_per], axis=1, join="inner").dropna()
paired["log_2022"] = np.log10(paired["er_2022"])
paired["log_2026"] = np.log10(paired["er_2026"])
paired["delta_log"] = paired["log_2026"] - paired["log_2022"]
log(f"  Survivors with ER in both years: {len(paired):,}")

t_stat, p_val = stats.ttest_rel(paired["log_2022"], paired["log_2026"])
mean_delta = paired["delta_log"].mean()
median_delta = paired["delta_log"].median()
log(f"  Paired t-test on log(er_pct): t={t_stat:+.2f}, p={p_val:.2e}")
log(f"  Mean Δlog10(ER) = {mean_delta:+.3f}  (≈ {10**mean_delta:.2f}× change)")
log(f"  Median ΔER: {paired['er_2022'].median():.3f}% → {paired['er_2026'].median():.3f}%")
share_decline = (paired["delta_log"] < 0).mean()
log(f"  Share of accounts whose ER fell: {share_decline*100:.1f}%")

# Table 7: longitudinal summary
long_rows = [
    {"metric": "YT 2022 cohort size (unique handles)",   "value": f"{len(cohort_2022):,}"},
    {"metric": "Attrition by 2026 (no usable data)",    "value": f"{attrition_rate*100:.1f}%"},
    {"metric": "Survivors with ER in both years",       "value": f"{len(paired):,}"},
    {"metric": "Median ER 2022 (survivors)",             "value": f"{paired['er_2022'].median():.3f}%"},
    {"metric": "Median ER 2026 (survivors)",             "value": f"{paired['er_2026'].median():.3f}%"},
    {"metric": "Mean Δlog10(ER)",                        "value": f"{mean_delta:+.3f}"},
    {"metric": "Paired t-statistic",                     "value": f"{t_stat:+.2f}"},
    {"metric": "p-value",                                "value": f"{p_val:.2e}"},
    {"metric": "Share of accounts with ER decline",     "value": f"{share_decline*100:.1f}%"},
]
save_table_png(pd.DataFrame(long_rows), TBL / "T6_longitudinal_yt.png",
    title="Table 6. YouTube 2022 → 2026 longitudinal paired analysis",
    fmt={"metric": str, "value": str})

# F5: paired-difference visualization
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
# Left: paired scatter (2022 vs 2026 ER), one point per survivor
axes[0].scatter(paired["log_2022"], paired["log_2026"], s=10, alpha=0.45,
                color=PLATFORM_COLOR["youtube"])
lims = [min(paired["log_2022"].min(), paired["log_2026"].min()),
        max(paired["log_2022"].max(), paired["log_2026"].max())]
axes[0].plot(lims, lims, color="black", lw=0.8, ls="--", label="y = x (no change)")
axes[0].set_xlabel("log10(ER) in 2022"); axes[0].set_ylabel("log10(ER) in 2026")
axes[0].set_title(f"Paired ER for {len(paired):,} surviving accounts")
axes[0].legend()
# Right: distribution of Δ
axes[1].hist(paired["delta_log"], bins=40, color=PLATFORM_COLOR["youtube"], alpha=0.8)
axes[1].axvline(0, color="black", lw=0.7, ls="--")
axes[1].axvline(mean_delta, color="red", lw=1.0, label=f"mean = {mean_delta:+.3f}")
axes[1].set_xlabel("Δ log10(ER)  (2026 − 2022)")
axes[1].set_ylabel("Number of accounts")
axes[1].set_title(f"Within-account change in ER, 2022→2026  (paired t = {t_stat:+.2f}, p = {p_val:.1e})")
axes[1].legend()
fig.suptitle("YouTube 2022 → 2026: longitudinal change for the same accounts", y=1.00)
fig.tight_layout(); fig.savefig(PLOT / "F5_yt_longitudinal.png", dpi=160); plt.close(fig)

# ==========================================================================
# T7. Summary table (renumbered)
# ==========================================================================
def stars(p): return "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "n.s."))
summary_rows = []
for plat in PLATFORMS_FULL:
    s, fit = ols_fits[plat]
    a_row = next(r for r in anova_rows if r["platform"].lower() == plat)
    summary_rows.append({
        "Platform": plat.capitalize(),
        "n (accounts)": len(s),
        "β log(followers)": f"{fit.params['log_followers']:+.3f} "
                            f"{stars(fit.pvalues['log_followers'])}",
        "ANOVA F (category)": f"{a_row['F']:.2f}",
        "η² (category)": f"{a_row['eta_squared']:.3f}",
        "OLS adj. R²": f"{fit.rsquared_adj:.3f}",
    })
# Add TikTok row with limited info
tt = slice_data("tiktok")
tt_r, tt_p = stats.pearsonr(tt["log_followers"], tt["log_er"])
summary_rows.insert(1, {
    "Platform": "TikTok",
    "n (accounts)": len(tt),
    "β log(followers)": f"Pearson r={tt_r:+.3f} {stars(tt_p)} (no category/country in source)",
    "ANOVA F (category)": "—", "η² (category)": "—", "OLS adj. R²": "—",
})
save_table_png(pd.DataFrame(summary_rows), TBL / "T7_summary.png",
    title="Table 6. Summary — RQ1 results across 2022 platforms",
    fmt={c: str for c in ["Platform","n (accounts)","β log(followers)",
                          "ANOVA F (category)","η² (category)","OLS adj. R²"]})

# ==========================================================================
# Save text summary
# ==========================================================================
(OUT / "summary.txt").write_text("\n".join(summary))
print(f"\nSaved summary to {OUT/'summary.txt'}")
print(f"Saved {len(list(TBL.glob('*.png')))} tables to {TBL}")
print(f"Saved {len(list(PLOT.glob('*.png')))} plots to {PLOT}")
