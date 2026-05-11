"""
Step 7: RQ1 — What features drive engagement rate?

Traditional statistical methods on log10(er_pct):
  - Pearson correlation (followers vs ER)
  - One-way ANOVA (ER across categories) + effect size (eta^2)
  - Multiple OLS regression with baselines (Beauty&Fashion, United States)
  - Backward variable selection by AIC
  - Logistic regression for top-quartile "high-engager"
  - Cross-year t-test on frame-comparable top-100 global subsets

Input:  4 - ER unified/finalData_with_er.csv
Output: 7 - statistical analysis/{plots,tables,summary.txt}
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor

ROOT = Path(__file__).resolve().parents[2]
SRC  = ROOT / "4 - ER unified" / "finalData_with_er.csv"
OUT  = ROOT / "7 - statistical analysis"
PLOT = OUT / "plots"
TBL  = OUT / "tables"
PLOT.mkdir(exist_ok=True, parents=True)
TBL.mkdir(exist_ok=True, parents=True)

PLATFORM_COLOR = {"instagram": "#E4405F", "tiktok": "#000000", "youtube": "#FF0000"}
SLICES = [("instagram", 2022), ("instagram", 2024),
          ("youtube",   2022), ("youtube",   2026)]
BASE_CATEGORY = "Entertainment"   # exists in every slice (Beauty&Fashion absent from YT 2026)
BASE_COUNTRY  = "United States"
TOP_K_COUNTRIES = 15

# IG 2024's `country` column is the LEADERBOARD country (from per-country source files),
# not the audience country — so we drop country from that slice's model.
COUNTRY_BAD_SLICES = {("instagram", 2024)}

summary = []
def log(msg=""):
    print(msg)
    summary.append(str(msg))

df_all = pd.read_csv(SRC, low_memory=False)
log(f"Loaded {len(df_all):,} rows from {SRC.name}")

def prep_slice(plat, yr, require_country=True):
    sub = df_all[(df_all["_platform"] == plat) & (df_all["_year"] == yr)
                 & df_all["er_pct"].notna() & (df_all["er_pct"] > 0)
                 & df_all["followers"].notna() & (df_all["followers"] > 0)
                 & df_all["category_unified"].notna()].copy()
    if require_country:
        sub = sub[sub["country"].notna()]
    # Restrict to top-K most frequent countries to avoid sparse cells
    if require_country:
        top_c = sub["country"].value_counts().head(TOP_K_COUNTRIES).index
        sub = sub[sub["country"].isin(top_c)]
    sub["log_er"] = np.log10(sub["er_pct"])
    sub["log_followers"] = np.log10(sub["followers"])
    # Drop duplicate handles (IG 2024 has 13 dupes from per-country leaderboards)
    sub = sub.drop_duplicates(subset=["handle"], keep="first")
    # Reorder categorical so baselines come first (for Treatment coding)
    return sub

# ==========================================================================
# 1. Pearson / Spearman: followers vs er_pct (per slice)
# ==========================================================================
log("\n" + "=" * 70)
log("1. CORRELATION — log(followers) vs log(er_pct), per slice")
log("=" * 70)
corr_rows = []
for plat, yr in SLICES:
    s = prep_slice(plat, yr, require_country=False)
    r_p, p_p = stats.pearsonr(s["log_followers"], s["log_er"])
    r_s, p_s = stats.spearmanr(s["log_followers"], s["log_er"])
    corr_rows.append({"platform": plat, "year": yr, "n": len(s),
                      "pearson_r": r_p, "pearson_p": p_p,
                      "spearman_r": r_s, "spearman_p": p_s})
    log(f"  {plat.capitalize()} {yr}: n={len(s):>5}  "
        f"Pearson r={r_p:+.3f} (p={p_p:.2e})  "
        f"Spearman ρ={r_s:+.3f} (p={p_s:.2e})")
pd.DataFrame(corr_rows).to_csv(TBL / "1_correlation_followers_er.csv", index=False)

# ==========================================================================
# 2. One-way ANOVA: log_er ~ category (per slice) + eta^2 effect size
# ==========================================================================
log("\n" + "=" * 70)
log("2. ONE-WAY ANOVA — log(er_pct) across category, per slice")
log("=" * 70)
anova_rows = []
for plat, yr in SLICES:
    s = prep_slice(plat, yr, require_country=False)
    groups = [g["log_er"].values for _, g in s.groupby("category_unified") if len(g) >= 5]
    if len(groups) < 2:
        continue
    F, p = stats.f_oneway(*groups)
    # eta^2 = SS_between / SS_total
    grand = np.concatenate(groups).mean()
    ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
    ss_total = sum(((np.concatenate(groups) - grand) ** 2))
    eta2 = ss_between / ss_total
    anova_rows.append({"platform": plat, "year": yr, "k_groups": len(groups),
                       "n": sum(len(g) for g in groups), "F": F, "p": p, "eta2": eta2})
    log(f"  {plat.capitalize()} {yr}: k={len(groups)} categories, "
        f"F={F:.2f}, p={p:.2e}, η²={eta2:.3f}")
pd.DataFrame(anova_rows).to_csv(TBL / "2_anova_category.csv", index=False)

# ==========================================================================
# 3. Multiple OLS: log_er ~ log_followers + C(category) + C(country)
# ==========================================================================
log("\n" + "=" * 70)
log(f"3. MULTIPLE OLS — log_er ~ log_followers + C(category) + C(country)")
log(f"   Baselines: category={BASE_CATEGORY!r}, country={BASE_COUNTRY!r}")
log("=" * 70)

ols_fits = {}
for plat, yr in SLICES:
    use_country = (plat, yr) not in COUNTRY_BAD_SLICES
    s = prep_slice(plat, yr, require_country=use_country)
    if BASE_CATEGORY not in s["category_unified"].unique():
        log(f"  [skip] {plat} {yr}: baseline category {BASE_CATEGORY!r} not in data")
        continue
    if use_country and BASE_COUNTRY not in s["country"].unique():
        log(f"  [skip] {plat} {yr}: baseline country {BASE_COUNTRY!r} not in data")
        continue
    terms = [f'C(category_unified, Treatment(reference="{BASE_CATEGORY}"))',
             "log_followers"]
    if use_country:
        terms.append(f'C(country, Treatment(reference="{BASE_COUNTRY}"))')
    else:
        log(f"  [note] {plat} {yr}: country regressor dropped (column is leaderboard, not audience)")
    formula = "log_er ~ " + " + ".join(terms)
    fit = smf.ols(formula, data=s).fit()
    ols_fits[(plat, yr)] = (s, fit)

    log(f"\n  --- {plat.capitalize()} {yr}: n={len(s):,}, "
        f"R²={fit.rsquared:.3f}, adj R²={fit.rsquared_adj:.3f}, AIC={fit.aic:.1f} ---")
    coef_tbl = pd.DataFrame({
        "coef":   fit.params,
        "std_err": fit.bse,
        "t":      fit.tvalues,
        "p":      fit.pvalues,
        "ci_lo":  fit.conf_int()[0],
        "ci_hi":  fit.conf_int()[1],
    })
    coef_tbl.to_csv(TBL / f"3_ols_{plat}_{yr}.csv")
    # Print only the meaningful rows
    sig = coef_tbl[coef_tbl["p"] < 0.05].sort_values("coef", ascending=False)
    log(f"  Significant terms (p<0.05): {len(sig)} / {len(coef_tbl)}")
    log(sig[["coef", "std_err", "p"]].round(3).to_string())

# ==========================================================================
# 4. Backward variable selection by AIC on the full OLS
# (block-level: drop entire categorical block if it doesn't lower AIC)
# ==========================================================================
log("\n" + "=" * 70)
log("4. BACKWARD VARIABLE SELECTION (by AIC, block-level)")
log("=" * 70)
for (plat, yr), (s, full_fit) in ols_fits.items():
    blocks = {
        "log_followers": "log_followers",
        "category":      f'C(category_unified, Treatment(reference="{BASE_CATEGORY}"))',
    }
    if (plat, yr) not in COUNTRY_BAD_SLICES:
        blocks["country"] = f'C(country, Treatment(reference="{BASE_COUNTRY}"))'
    log(f"\n  {plat.capitalize()} {yr}  (full AIC = {full_fit.aic:.1f})")
    for drop_name, drop_term in blocks.items():
        remaining = [t for n, t in blocks.items() if n != drop_name]
        formula = "log_er ~ 1" if not remaining else "log_er ~ " + " + ".join(remaining)
        try:
            reduced = smf.ols(formula, data=s).fit()
            delta = reduced.aic - full_fit.aic
            keep = "KEEP" if delta > 0 else "DROP-OK"
            log(f"    drop {drop_name:>14}: AIC={reduced.aic:8.1f}  ΔAIC={delta:+7.1f}  → {keep}")
        except Exception as e:
            log(f"    drop {drop_name}: failed ({e})")

# ==========================================================================
# 5. Logistic regression: P(top-quartile ER | features), per slice
# ==========================================================================
log("\n" + "=" * 70)
log("5. LOGISTIC REGRESSION — P(top-quartile ER | log_followers + cat + country)")
log("=" * 70)
logit_fits = {}
for plat, yr in SLICES:
    use_country = (plat, yr) not in COUNTRY_BAD_SLICES
    s = prep_slice(plat, yr, require_country=use_country)
    if BASE_CATEGORY not in s["category_unified"].unique(): continue
    if use_country and BASE_COUNTRY not in s["country"].unique(): continue
    q75 = s["log_er"].quantile(0.75)
    s["high_er"] = (s["log_er"] >= q75).astype(int)
    terms = [f'C(category_unified, Treatment(reference="{BASE_CATEGORY}"))', "log_followers"]
    if use_country:
        terms.append(f'C(country, Treatment(reference="{BASE_COUNTRY}"))')
    formula = "high_er ~ " + " + ".join(terms)
    try:
        fit = smf.logit(formula, data=s).fit(disp=False, maxiter=200)
    except Exception as e:
        log(f"  [fail] {plat} {yr}: {e}")
        continue
    logit_fits[(plat, yr)] = fit
    log(f"\n  --- {plat.capitalize()} {yr}: n={len(s):,}, "
        f"pseudo-R²={fit.prsquared:.3f}, LL={fit.llf:.1f} ---")
    tbl = pd.DataFrame({
        "coef": fit.params,
        "odds_ratio": np.exp(fit.params),
        "p":    fit.pvalues,
        "or_ci_lo": np.exp(fit.conf_int()[0]),
        "or_ci_hi": np.exp(fit.conf_int()[1]),
    })
    tbl.to_csv(TBL / f"5_logit_{plat}_{yr}.csv")
    sig = tbl[tbl["p"] < 0.05].sort_values("odds_ratio", ascending=False)
    log(f"  Significant terms (p<0.05): {len(sig)} / {len(tbl)}")
    log(sig[["odds_ratio", "or_ci_lo", "or_ci_hi", "p"]].round(3).to_string())

# ==========================================================================
# 6. Cross-year t-test on frame-comparable top-100 global subsets
# ==========================================================================
log("\n" + "=" * 70)
log("6. CROSS-YEAR t-TEST (frame-comparable top-100 global subsets)")
log("=" * 70)
def top100(plat, yr):
    if yr == 2024:
        return df_all[(df_all["_platform"] == plat) & (df_all["_year"] == yr)
                      & (df_all["_is_global"] == True)
                      & df_all["er_pct"].notna() & (df_all["er_pct"] > 0)].copy()
    # 2022 (top-1000 global) or 2026 (998-row global) → take top-100 by followers
    sub = df_all[(df_all["_platform"] == plat) & (df_all["_year"] == yr)
                 & df_all["er_pct"].notna() & (df_all["er_pct"] > 0)
                 & df_all["followers"].notna()].copy()
    if yr == 2022:
        # 2022 has 5 monthly rows per account; take one row per handle (highest followers)
        sub = sub.sort_values("followers", ascending=False).drop_duplicates("handle")
    sub["log_er"] = np.log10(sub["er_pct"])
    return sub.nlargest(100, "followers")

cross_year_pairs = [("instagram", 2022, 2024), ("youtube", 2022, 2026)]
ttest_rows = []
for plat, y1, y2 in cross_year_pairs:
    a = top100(plat, y1); a["log_er"] = np.log10(a["er_pct"])
    b = top100(plat, y2); b["log_er"] = np.log10(b["er_pct"])
    t, p = stats.ttest_ind(a["log_er"], b["log_er"], equal_var=False)
    md_a, md_b = a["er_pct"].median(), b["er_pct"].median()
    ttest_rows.append({"platform": plat, "year_a": y1, "year_b": y2,
                       "n_a": len(a), "n_b": len(b),
                       "median_er_a": md_a, "median_er_b": md_b,
                       "t": t, "p": p})
    log(f"  {plat.capitalize()} {y1} (n={len(a)}, median ER={md_a:.2f}%) vs "
        f"{y2} (n={len(b)}, median ER={md_b:.2f}%): "
        f"t={t:+.2f}, p={p:.2e}")
pd.DataFrame(ttest_rows).to_csv(TBL / "6_ttest_cross_year_top100.csv", index=False)

# ==========================================================================
# 7. Forest plot: OLS category coefficients across slices
# ==========================================================================
log("\n" + "=" * 70)
log("7. FOREST PLOT — category coefficients across slices")
log("=" * 70)
fig, axes = plt.subplots(2, 2, figsize=(13, 9))
axes = axes.flatten()
for ax, ((plat, yr), (s, fit)) in zip(axes, ols_fits.items()):
    cat_terms = [p for p in fit.params.index if "category_unified" in p]
    coefs = fit.params[cat_terms]
    ci = fit.conf_int().loc[cat_terms]
    labels = [t.split('T.')[-1].rstrip(']') for t in cat_terms]
    order = coefs.sort_values().index
    coefs = coefs.loc[order]; ci = ci.loc[order]
    labels = [t.split('T.')[-1].rstrip(']') for t in order]
    y_pos = np.arange(len(coefs))
    ax.errorbar(coefs.values, y_pos,
                xerr=[coefs.values - ci[0].values, ci[1].values - coefs.values],
                fmt="o", color=PLATFORM_COLOR[plat], capsize=3)
    ax.axvline(0, color="gray", lw=0.5, ls=":")
    ax.set_yticks(y_pos); ax.set_yticklabels(labels)
    ax.set_xlabel(f"Δ log10(er_pct) vs {BASE_CATEGORY}")
    ax.set_title(f"{plat.capitalize()} {yr}  (R²={fit.rsquared:.2f}, n={len(s):,})")
fig.suptitle("Category effect on engagement rate (OLS, with 95% CI)", y=1.00)
fig.tight_layout()
fig.savefig(PLOT / "F1_category_coefficients.png", dpi=140)
plt.close(fig)
log(f"  Saved {PLOT/'F1_category_coefficients.png'}")

# ==========================================================================
# F2. Country coefficients forest plot (slices that included country)
# ==========================================================================
country_slices = [(k, v) for k, v in ols_fits.items() if k not in COUNTRY_BAD_SLICES]
if country_slices:
    n = len(country_slices)
    fig, axes = plt.subplots(1, n, figsize=(5.5 * n, 7), squeeze=False)
    axes = axes.flatten()
    for ax, ((plat, yr), (s, fit)) in zip(axes, country_slices):
        terms = [p for p in fit.params.index if "country" in p]
        coefs = fit.params[terms]
        ci = fit.conf_int().loc[terms]
        order = coefs.sort_values().index
        coefs = coefs.loc[order]; ci = ci.loc[order]
        labels = [t.split('T.')[-1].rstrip(']') for t in order]
        y_pos = np.arange(len(coefs))
        ax.errorbar(coefs.values, y_pos,
                    xerr=[coefs.values - ci[0].values, ci[1].values - coefs.values],
                    fmt="o", color=PLATFORM_COLOR[plat], capsize=3)
        ax.axvline(0, color="gray", lw=0.5, ls=":")
        ax.set_yticks(y_pos); ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel(f"Δ log10(er_pct) vs {BASE_COUNTRY}")
        ax.set_title(f"{plat.capitalize()} {yr}  (n={len(s):,})")
    fig.suptitle("Country effect on engagement rate (OLS, with 95% CI)", y=1.00)
    fig.tight_layout()
    fig.savefig(PLOT / "F2_country_coefficients.png", dpi=140)
    plt.close(fig)
    log(f"\n  Saved {PLOT/'F2_country_coefficients.png'}")

# ==========================================================================
# F3. log_followers coefficient across slices (single bar chart)
# ==========================================================================
fig, ax = plt.subplots(figsize=(8, 4.5))
slice_labels, betas, ses, colors = [], [], [], []
for (plat, yr), (s, fit) in ols_fits.items():
    slice_labels.append(f"{plat.capitalize()}\n{yr}")
    betas.append(fit.params["log_followers"])
    ses.append(fit.bse["log_followers"])
    colors.append(PLATFORM_COLOR[plat])
x_pos = np.arange(len(slice_labels))
ax.bar(x_pos, betas, yerr=[1.96 * se for se in ses], capsize=4,
       color=colors, alpha=0.75, edgecolor="white")
for i, b in enumerate(betas):
    ax.text(i, b - 0.05 if b < 0 else b + 0.05, f"{b:+.2f}",
            ha="center", va="top" if b < 0 else "bottom", fontsize=9)
ax.set_xticks(x_pos); ax.set_xticklabels(slice_labels)
ax.axhline(0, color="gray", lw=0.5, ls=":")
ax.set_ylabel("OLS β  for  log10(followers)")
ax.set_title("Effect of audience size on engagement rate (per slice, with 95% CI)")
fig.tight_layout()
fig.savefig(PLOT / "F3_log_followers_beta.png", dpi=140)
plt.close(fig)
log(f"  Saved {PLOT/'F3_log_followers_beta.png'}")

# ==========================================================================
# F4. Cross-year t-test visualization (boxplots of top-100 matched subsets)
# ==========================================================================
fig, axes = plt.subplots(1, len(cross_year_pairs), figsize=(5.5 * len(cross_year_pairs), 5),
                        squeeze=False)
axes = axes.flatten()
for ax, (plat, y1, y2) in zip(axes, cross_year_pairs):
    a = top100(plat, y1); a["log_er"] = np.log10(a["er_pct"])
    b = top100(plat, y2); b["log_er"] = np.log10(b["er_pct"])
    bp = ax.boxplot([a["log_er"].values, b["log_er"].values],
                    labels=[f"{y1}\n(n={len(a)})", f"{y2}\n(n={len(b)})"],
                    patch_artist=True, showfliers=False)
    for patch in bp["boxes"]:
        patch.set_facecolor(PLATFORM_COLOR[plat]); patch.set_alpha(0.6)
    t, p = stats.ttest_ind(a["log_er"], b["log_er"], equal_var=False)
    sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
    ax.set_title(f"{plat.capitalize()}: {y1} vs {y2}\nt={t:+.2f}, p={p:.1e} ({sig})")
    ax.set_ylabel("log10(er_pct %)")
    ax.axhline(0, color="gray", lw=0.5, ls=":")
fig.suptitle("Cross-year ER on frame-matched top-100 global subsets", y=1.00)
fig.tight_layout()
fig.savefig(PLOT / "F4_cross_year_ttest.png", dpi=140)
plt.close(fig)
log(f"  Saved {PLOT/'F4_cross_year_ttest.png'}")

# ==========================================================================
# F5. Logistic regression odds ratios — significant category effects per slice
# ==========================================================================
n_logit = len(logit_fits)
if n_logit:
    fig, axes = plt.subplots(1, n_logit, figsize=(5.5 * n_logit, 5.5), squeeze=False)
    axes = axes.flatten()
    for ax, ((plat, yr), fit) in zip(axes, logit_fits.items()):
        cat_terms = [p for p in fit.params.index if "category_unified" in p]
        or_vals = np.exp(fit.params[cat_terms])
        ci = np.exp(fit.conf_int().loc[cat_terms])
        order = or_vals.sort_values().index
        or_vals = or_vals.loc[order]; ci = ci.loc[order]
        labels = [t.split('T.')[-1].rstrip(']') for t in order]
        y_pos = np.arange(len(or_vals))
        ax.errorbar(or_vals.values, y_pos,
                    xerr=[or_vals.values - ci[0].values, ci[1].values - or_vals.values],
                    fmt="o", color=PLATFORM_COLOR[plat], capsize=3)
        ax.axvline(1, color="gray", lw=0.5, ls=":")  # OR=1 means no effect
        ax.set_xscale("log")
        ax.set_yticks(y_pos); ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel("Odds ratio (vs Entertainment)")
        ax.set_title(f"{plat.capitalize()} {yr}\nP(top-quartile ER)")
    fig.suptitle("Logistic regression: category odds of being a high-engager", y=1.00)
    fig.tight_layout()
    fig.savefig(PLOT / "F5_logit_category_OR.png", dpi=140)
    plt.close(fig)
    log(f"  Saved {PLOT/'F5_logit_category_OR.png'}")

# ==========================================================================
# 8. Save summary
# ==========================================================================
(OUT / "summary.txt").write_text("\n".join(summary))
print(f"\nSaved summary to {OUT/'summary.txt'}")
print(f"Saved {len(list(TBL.glob('*.csv')))} tables to {TBL}")
print(f"Saved {len(list(PLOT.glob('*.png')))} plots to {PLOT}")
