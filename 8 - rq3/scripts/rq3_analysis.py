# =============================================================================
# RQ3: Is the "micro-influencer advantage" real, and does it vary by platform?
# =============================================================================
# Data: December 2022 snapshot — Instagram, TikTok, YouTube (~1,000 per platform)
# Single month used for: consistent sample size across platforms, avoidance of
# repeated-measures inflation from 5 monthly snapshots, and alignment with the
# dataset's stated scope of top-1,000 per platform per month.
#
# Methods:
#   1. Within-platform quartile tier definition
#   2. Permutation test (F-statistic, 10,000 shuffles) — per platform
#   3. Bootstrap 95% CI for median ER per tier x platform
#   4. Wilcoxon rank-sum test: Q1 vs Q4 per platform
#   5. Category-stratified tier analysis (Wilcoxon rank-sum per category)
#   6. Temporal stability on matched creators (Instagram only)
#      a. Wilcoxon signed-rank per tier (2022 vs 2024)
#      b. Bootstrap DeltaEffect on matched Q1-Q4 gap
#
# Outputs (saved to 8 - rq3/plots/):
#   - tier_definition.png
#   - permutation_test.png
#   - bootstrap_ci_tiers.png
#   - wilcoxon_ranksum.png
#   - category_stratified_instagram.png
#   - temporal_matched.png
# =============================================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import f_oneway, mannwhitneyu, wilcoxon

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE      = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE / "4 - ER unified" / "finalData_with_er_yt_with_views.csv"
OUT_PATH  = BASE / "8 - rq3" / "plots"
OUT_PATH.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
TIER_ORDER  = ['Q1', 'Q2', 'Q3', 'Q4']
TIER_LABELS = ['Q1', 'Q2', 'Q3', 'Q4']
PLATFORMS   = ['instagram', 'tiktok', 'youtube']
COLORS      = {'instagram': '#E1306C', 'tiktok': '#010101', 'youtube': '#FF0000'}
B           = 10_000
SEED        = 42
x           = np.arange(4)


# =============================================================================
# LOAD DATA
# =============================================================================
df = pd.read_csv(DATA_PATH, low_memory=False)


# =============================================================================
# STEP 1 — Filter to December 2022 and define within-platform quartile tiers
# =============================================================================
df22 = df[
    (df['_year'] == 2022) &
    (df['_month'] == 'december')
].copy()
df22 = df22[df22['er_pct'].notna() & df22['followers'].notna()]

df22['tier'] = df22.groupby('_platform')['followers'].transform(
    lambda x: pd.qcut(x, q=4, labels=TIER_ORDER)
)

print("── Tier counts and median ER (December 2022) ──")
print(df22.groupby(['_platform', 'tier'])['er_pct'].agg(['count', 'median']).round(3))

print("\n── Follower ranges per tier (December 2022) ──")
print(df22.groupby(['_platform', 'tier'])['followers'].describe()[['min', '50%', 'max']].round(0))


# =============================================================================
# STEP 2 — Permutation test (F-statistic, 10,000 shuffles)
# =============================================================================
def permutation_f_test(data, labels, n_permutations=B, random_state=SEED):
    """
    Nonparametric test for tier effect on ER.
    Uses F-statistic as test statistic; p = proportion of permuted
    F-statistics >= observed F.
    No normality assumption required (unlike standard ANOVA).
    Exchangeability under H0: tier label has no effect on er_pct.
    """
    rng    = np.random.default_rng(random_state)
    groups = [data[labels == l] for l in np.unique(labels)]
    obs_f  = f_oneway(*groups).statistic
    perm_f = np.array([
        f_oneway(*[data[rng.permutation(labels) == l]
                   for l in np.unique(labels)]).statistic
        for _ in range(n_permutations)
    ])
    p_val = np.mean(perm_f >= obs_f)
    return obs_f, p_val, perm_f

print("\n── Permutation Test Results (December 2022) ──")
print("-" * 45)
perm_results = {}
for platform in PLATFORMS:
    sub = df22[df22['_platform'] == platform].dropna(subset=['er_pct', 'tier'])
    f_stat, p_val, perm_f = permutation_f_test(
        sub['er_pct'].values, sub['tier'].values
    )
    perm_results[platform] = {'f_stat': f_stat, 'p_val': p_val, 'perm_f': perm_f}
    p_str = f"{p_val:.4f}" if p_val > 0 else "< 0.0001"
    print(f"{platform:12s} | F = {f_stat:.2f} | p = {p_str}")


# =============================================================================
# STEP 3 — Bootstrap 95% CI for median ER per tier x platform
# =============================================================================
def bootstrap_median_ci(data, B=B, random_state=SEED):
    """
    Percentile bootstrap CI for median ER.
    Median used (not mean) because er_pct is right-skewed.
    B=10,000 resamples with replacement.
    """
    rng     = np.random.default_rng(random_state)
    medians = np.array([
        np.median(rng.choice(data, size=len(data), replace=True))
        for _ in range(B)
    ])
    return np.percentile(medians, [2.5, 97.5])

print("\n── Bootstrap 95% CI for Median ER per Tier x Platform ──")
print("-" * 55)
ci_rows = []
for platform in PLATFORMS:
    for tier in TIER_ORDER:
        sub = df22[
            (df22['_platform'] == platform) &
            (df22['tier'] == tier)
        ]['er_pct'].dropna().values
        ci_low, ci_high = bootstrap_median_ci(sub)
        med = np.median(sub)
        ci_rows.append({
            'platform': platform, 'tier': tier,
            'median': med, 'ci_low': ci_low, 'ci_high': ci_high
        })
        print(f"{platform:12s} {tier:4s} | median = {med:.3f} | "
              f"CI = [{ci_low:.3f}, {ci_high:.3f}]")

ci_df = pd.DataFrame(ci_rows)


# =============================================================================
# STEP 4 — Wilcoxon rank-sum test: Q1 vs Q4 per platform
# =============================================================================
# Tests whether Q1 ER distribution is stochastically larger than Q4.
# Independent groups test — no normality assumption.
# Complements permutation test: while permutation tests overall tier effect,
# rank-sum isolates the extreme boundary comparison.

print("\n── Wilcoxon Rank-Sum Test: Q1 vs Q4 (December 2022) ──")
print("-" * 55)
ranksum_results = {}
for platform in PLATFORMS:
    sub = df22[df22['_platform'] == platform].dropna(subset=['er_pct', 'tier'])
    q1  = sub[sub['tier'] == 'Q1']['er_pct'].values
    q4  = sub[sub['tier'] == 'Q4']['er_pct'].values
    stat, p = mannwhitneyu(q1, q4, alternative='greater')
    ranksum_results[platform] = {'stat': stat, 'p': p}
    p_str = "< 0.0001" if p < 0.0001 else f"{p:.4f}"
    print(f"{platform:12s} | U = {stat:.1f} | p = {p_str}")


# =============================================================================
# STEP 5 — Category-stratified tier analysis
# =============================================================================
# Tests whether the micro-influencer advantage holds within each content
# category, or is driven by category composition differences across tiers.
# Wilcoxon rank-sum Q1 vs Q4 per category per platform.
# Minimum n=50 per category, n>=10 per tier required.

print("\n── Category-Stratified Tier Analysis ──")
cat_results_all = {}
for platform in PLATFORMS:
    print(f"\n{platform.upper()}")
    print("-" * 60)
    sub_plt = df22[
        (df22['_platform'] == platform) &
        df22['category_unified'].notna()
    ].copy()
    cat_results = []
    for cat in sub_plt['category_unified'].unique():
        sub = sub_plt[sub_plt['category_unified'] == cat]
        if len(sub) < 50:
            continue
        q1 = sub[sub['tier'] == 'Q1']['er_pct'].values
        q4 = sub[sub['tier'] == 'Q4']['er_pct'].values
        if len(q1) < 10 or len(q4) < 10:
            continue
        stat, p = mannwhitneyu(q1, q4, alternative='greater')
        gap = np.median(q1) - np.median(q4)
        cat_results.append({
            'category': cat, 'n': len(sub),
            'q1_med': np.median(q1), 'q4_med': np.median(q4),
            'gap': gap, 'p': p
        })
        p_str = "< 0.0001" if p < 0.0001 else f"{p:.4f}"
        print(f"{cat:20s} | n={len(sub):3d} | Q1={np.median(q1):.2f} "
              f"| Q4={np.median(q4):.2f} | gap={gap:.2f} | p={p_str}")
    cat_results_all[platform] = pd.DataFrame(cat_results)


# =============================================================================
# STEP 6 — Temporal stability on matched creators (Instagram only)
# =============================================================================
# Uses entity resolution uniqueId to match same creators across 2022 and 2024.
# a. Wilcoxon signed-rank: did ER change significantly per tier?
# b. Bootstrap DeltaEffect: did the Q1-Q4 gap change significantly?
# Instagram only — most reliable er_pct coverage in 2024 (98.9%)

print("\n── Temporal Stability: Matched Instagram Creators ──")
print("-" * 55)

# Find matched creators
ig_dec22 = df[
    (df['_platform'] == 'instagram') &
    (df['_year'] == 2022) &
    (df['_month'] == 'december')
].copy()
ig_2024 = df[
    (df['_platform'] == 'instagram') &
    (df['_year'] == 2024)
].copy()

creators_dec22 = set(ig_dec22['uniqueId'].dropna())
creators_2024  = set(ig_2024['uniqueId'].dropna())
matched_ids    = creators_dec22.intersection(creators_2024)
print(f"Matched creators (Dec 2022 x 2024): {len(matched_ids)}")

# Build matched dataframe
ig_matched_22 = ig_dec22[ig_dec22['uniqueId'].isin(matched_ids)][
    ['uniqueId', 'er_pct', 'followers']
].copy()
ig_matched_24 = ig_2024[ig_2024['uniqueId'].isin(matched_ids)][
    ['uniqueId', 'er_pct', 'followers']
].copy()

matched_df = ig_matched_22.merge(
    ig_matched_24, on='uniqueId', suffixes=('_22', '_24')
)
matched_df = matched_df.dropna(subset=['er_pct_22', 'er_pct_24', 'followers_22'])
matched_df['tier'] = pd.qcut(
    matched_df['followers_22'], q=4, labels=TIER_ORDER
)
print(f"Matched pairs with complete data: {len(matched_df)}")
print(matched_df.groupby('tier')[['er_pct_22', 'er_pct_24']].median().round(3))

# 6a. Wilcoxon signed-rank per tier
print("\nWilcoxon Signed-Rank: ER change per tier (2022 vs 2024)")
print("-" * 55)
for tier in TIER_ORDER:
    sub = matched_df[matched_df['tier'] == tier]
    stat, p = wilcoxon(sub['er_pct_22'], sub['er_pct_24'])
    direction = "decreased" if sub['er_pct_22'].median() > sub['er_pct_24'].median() else "increased"
    p_str = "< 0.0001" if p < 0.0001 else f"{p:.4f}"
    print(f"{tier} (n={len(sub)}) | W = {stat:.1f} | p = {p_str} | ER {direction}")

# 6b. Bootstrap DeltaEffect
def bootstrap_delta_matched(df_matched, B=B, random_state=SEED):
    """Bootstrap CI for change in Q1-Q4 gap between 2022 and 2024."""
    rng    = np.random.default_rng(random_state)
    deltas = []
    for _ in range(B):
        sample  = df_matched.sample(n=len(df_matched), replace=True,
                                    random_state=None)
        q1      = sample[sample['tier'] == 'Q1']
        q4      = sample[sample['tier'] == 'Q4']
        gap_22  = q1['er_pct_22'].median() - q4['er_pct_22'].median()
        gap_24  = q1['er_pct_24'].median() - q4['er_pct_24'].median()
        deltas.append(gap_24 - gap_22)
    deltas   = np.array(deltas)
    q1_all   = df_matched[df_matched['tier'] == 'Q1']
    q4_all   = df_matched[df_matched['tier'] == 'Q4']
    observed = (q1_all['er_pct_24'].median() - q4_all['er_pct_24'].median()) - \
               (q1_all['er_pct_22'].median() - q4_all['er_pct_22'].median())
    ci       = np.percentile(deltas, [2.5, 97.5])
    return observed, ci, deltas

obs, ci, boot = bootstrap_delta_matched(matched_df)
sig = "SIGNIFICANT" if ci[0] > 0 or ci[1] < 0 else "NOT significant"
print(f"\nDeltaEffect = {obs:.3f}% | CI = [{ci[0]:.3f}, {ci[1]:.3f}]")
print(f"-> Change is {sig} (CI {'excludes' if sig == 'SIGNIFICANT' else 'includes'} zero)")


# =============================================================================
# PLOTS
# =============================================================================

# ── Plot 1: Tier definition ───────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(14, 6))

all_vals   = df22['followers'].dropna().values
global_min = all_vals.min() * 0.5
global_max = all_vals.max() * 2

for ax, platform in zip(axes, PLATFORMS):
    color      = COLORS[platform]
    sub        = df22[df22['_platform'] == platform].copy()
    tier_stats = sub.groupby('tier')['followers'].agg(['min', 'median', 'max'])

    for i, tier in enumerate(TIER_ORDER):
        row = tier_stats.loc[tier]
        ax.bar(i, row['max'] - row['min'], bottom=row['min'],
               color=color, alpha=0.25, width=0.6,
               edgecolor=color, linewidth=0.8)
        ax.plot(i, row['median'], 'o', color=color, markersize=9, zorder=5)
        ax.text(i, row['median'] * 1.4,
                f"{row['median']/1e6:.0f}M",
                ha='center', va='bottom', fontsize=9,
                fontweight='bold', color=color)

    ax.set_xticks(range(4))
    ax.set_xticklabels(TIER_LABELS, fontsize=11)
    ax.set_yscale('log')
    ax.set_ylim(global_min, global_max)
    ax.set_ylabel('Followers (log scale)' if platform == 'instagram' else '')
    ax.set_title(platform.capitalize(), fontweight='bold', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

fig.suptitle(
    'Follower Range per Tier x Platform (December 2022)\n'
    'Bar = min-max range,  dot = median',
    fontweight='bold', fontsize=13
)
plt.tight_layout()
plt.savefig(OUT_PATH / 'tier_definition.png', bbox_inches='tight', dpi=150)
plt.close()
print("\n✅ Plot 1 saved: tier_definition.png")


# ── Plot 2: Permutation test ──────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(14, 4))

for ax, platform in zip(axes, PLATFORMS):
    res    = perm_results[platform]
    obs_f  = res['f_stat']
    perm_f = res['perm_f']
    p_val  = res['p_val']
    p_str  = "p < 0.0001" if p_val == 0 else f"p = {p_val:.4f}"

    ax.hist(perm_f, bins=60, color=COLORS[platform], alpha=0.6, edgecolor='white')
    ax.axvline(obs_f, color='black', linewidth=2,
               label=f'Observed F = {obs_f:.1f}')
    if platform == 'instagram':
        ax.set_xscale('log')
        ax.set_xlabel('F-statistic (permuted, log scale)')
    else:
        ax.set_xlabel('F-statistic (permuted)')
    ax.set_ylabel('Frequency')
    ax.set_title(platform.capitalize(), fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(axis='y', alpha=0.3)
    ax.text(0.97, 0.95, p_str,
            transform=ax.transAxes, ha='right', va='top',
            fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

fig.suptitle(
    'Permutation Test: Null Distribution of F-statistic (December 2022)\n'
    '10,000 shuffles of tier labels',
    fontweight='bold'
)
plt.tight_layout()
plt.savefig(OUT_PATH / 'permutation_test.png', bbox_inches='tight', dpi=150)
plt.close()
print("✅ Plot 2 saved: permutation_test.png")


# ── Plot 3: Bootstrap CI ──────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=False)

for ax, platform in zip(axes, PLATFORMS):
    sub      = ci_df[ci_df['platform'] == platform]
    medians  = sub['median'].values
    ci_low   = sub['ci_low'].values
    ci_high  = sub['ci_high'].values
    err_low  = medians - ci_low
    err_high = ci_high - medians

    ax.errorbar(x, medians,
                yerr=[err_low, err_high],
                fmt='o-', color=COLORS[platform],
                capsize=5, linewidth=2, markersize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(TIER_LABELS)
    ax.set_title(platform.capitalize(), fontsize=13, fontweight='bold')
    ax.set_xlabel('Follower Tier')
    ax.set_ylabel('Median ER (%)')
    ax.grid(axis='y', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

fig.suptitle(
    'Median ER by Follower Tier (December 2022)\n'
    'with Bootstrap 95% CI  |  Note: y-axes scaled independently per platform',
    fontsize=13, fontweight='bold', y=1.02
)
plt.tight_layout()
plt.savefig(OUT_PATH / 'bootstrap_ci_tiers.png', bbox_inches='tight', dpi=150)
plt.close()
print("✅ Plot 3 saved: bootstrap_ci_tiers.png")


# ── Plot 4: Wilcoxon rank-sum ─────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=False)

for ax, platform in zip(axes, PLATFORMS):
    color   = COLORS[platform]
    sub     = df22[df22['_platform'] == platform].dropna(subset=['er_pct', 'tier'])
    res     = ranksum_results[platform]
    p_str   = "p < 0.0001" if res['p'] < 0.0001 else f"p = {res['p']:.4f}"
    medians = [sub[sub['tier'] == t]['er_pct'].median() for t in TIER_ORDER]

    ax.bar(TIER_ORDER, medians, color=color, alpha=0.7, edgecolor=color)
    ax.set_title(platform.capitalize(), fontweight='bold', fontsize=13)
    ax.set_xlabel('Follower Tier')
    ax.set_ylabel('Median ER (%)')
    ax.grid(axis='y', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.text(0.97, 0.97, f"Q1 vs Q4\n{p_str}",
            transform=ax.transAxes, ha='right', va='top',
            fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

fig.suptitle(
    'Wilcoxon Rank-Sum Test: Q1 vs Q4 ER (December 2022)\n'
    'Bars = median ER per tier',
    fontweight='bold', fontsize=13
)
plt.tight_layout()
plt.savefig(OUT_PATH / 'wilcoxon_ranksum.png', bbox_inches='tight', dpi=150)
plt.close()
print("✅ Plot 4 saved: wilcoxon_ranksum.png")


# ── Plot 5: Category-stratified Instagram ─────────────────────────────────────
cat_df = cat_results_all['instagram'].sort_values('gap', ascending=True)

fig, ax = plt.subplots(figsize=(10, 5))
ax.barh(cat_df['category'], cat_df['gap'],
        color='#E1306C', alpha=0.7, edgecolor='#E1306C')
ax.axvline(0, color='black', linewidth=0.8)
ax.set_xlabel('Q1 − Q4 Median ER Gap (%)')
ax.set_title(
    'Micro-Influencer Advantage by Category\n'
    'Instagram December 2022 (all p < 0.0001)',
    fontweight='bold', fontsize=13
)
ax.grid(axis='x', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

for _, row in cat_df.iterrows():
    idx = list(cat_df['category']).index(row['category'])
    ax.text(row['gap'] + 0.1, idx, f"n={row['n']}",
            va='center', fontsize=9)

plt.tight_layout()
plt.savefig(OUT_PATH / 'category_stratified_instagram.png',
            bbox_inches='tight', dpi=150)
plt.close()
print("✅ Plot 5 saved: category_stratified_instagram.png")


# ── Plot 6: Temporal matched creators ────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Left: tier ER 2022 vs 2024
ax = axes[0]
x4    = np.arange(4)
med22 = [matched_df[matched_df['tier'] == t]['er_pct_22'].median()
         for t in TIER_ORDER]
med24 = [matched_df[matched_df['tier'] == t]['er_pct_24'].median()
         for t in TIER_ORDER]

ax.plot(x4, med22, 'o-',  color='#E1306C', linewidth=2,
        markersize=7, label='2022')
ax.plot(x4, med24, 'o--', color='#880E4F', linewidth=2,
        markersize=7, label='2024')
ax.set_xticks(x4)
ax.set_xticklabels(TIER_LABELS)
ax.set_xlabel('Follower Tier (defined by 2022 followers)')
ax.set_ylabel('Median ER (%)')
ax.set_title(f'Instagram: Matched Creators\nTier ER by Year (n={len(matched_df)})',
             fontweight='bold')
ax.legend()
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Right: bootstrap DeltaEffect distribution
ax = axes[1]
ax.hist(boot, bins=80, color='#E1306C', alpha=0.7, edgecolor='white')
ax.axvline(obs,   color='black', linewidth=2,
           label=f'ΔEffect = {obs:.2f}%')
ax.axvline(ci[0], color='gray',  linestyle='--',
           linewidth=1.5, label='95% CI')
ax.axvline(ci[1], color='gray',  linestyle='--', linewidth=1.5)
ax.axvline(0,     color='red',   linestyle=':',
           linewidth=1.5, label='Zero (no change)')
ax.set_xlabel('ΔEffect (2024 − 2022)')
ax.set_ylabel('Frequency')
ax.set_title('Bootstrap Distribution of ΔEffect\n'
             '(Matched Instagram Q1−Q4 gap change)',
             fontweight='bold')
ax.legend(fontsize=8)
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig(OUT_PATH / 'temporal_matched.png', bbox_inches='tight', dpi=150)
plt.close()
print("✅ Plot 6 saved: temporal_matched.png")

print("\n✅ All done. Results and plots saved to:", OUT_PATH)