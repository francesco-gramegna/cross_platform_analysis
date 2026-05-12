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
#
# Temporal analysis (Bootstrap DeltaEffect) was considered but dropped:
#   - 2022 top-100 Instagram shows no tier effect (compressed follower range)
#   - 2024 all-countries Instagram has insufficient power (n=97, ~24 per tier)
#   - Sampling frames are not comparable across years
#   -> Left as future work requiring matched sampling frames
#
# Outputs (saved to 8 - rq3/plots/):
#   - tier_definition.png
#   - permutation_test.png
#   - bootstrap_ci_tiers.png
# =============================================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import f_oneway

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE      = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE / "4 - ER unified" / "finalData_with_er.csv"
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
# December 2022 chosen as the most recent 2022 snapshot, giving ~1,000 records
# per platform — consistent sample sizes and no repeated-measures inflation.

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
# PLOTS
# =============================================================================

# ── Plot 1: Tier definition — follower range per tier x platform ──────────────
fig, axes = plt.subplots(1, 3, figsize=(14, 6))

all_vals = df22['followers'].dropna().values
global_min = all_vals.min() * 0.5
global_max = all_vals.max() * 2

for ax, platform, color in zip(axes, PLATFORMS, COLORS.values()):
    sub = df22[df22['_platform'] == platform].copy()
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


# ── Plot 2: Permutation test null distributions ───────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(14, 4))

for ax, platform in zip(axes, PLATFORMS):
    res    = perm_results[platform]
    obs_f  = res['f_stat']
    perm_f = res['perm_f']
    p_val  = res['p_val']
    p_str  = f"p = {p_val:.4f}" if p_val > 0 else "p < 0.0001"

    ax.hist(perm_f, bins=60, color=COLORS[platform], alpha=0.6, edgecolor='white')
    ax.axvline(obs_f, color='black', linewidth=2,
               label=f'Observed F = {obs_f:.1f}')
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


# ── Plot 3: Bootstrap CI interaction chart ────────────────────────────────────
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

print("\n✅ All done. Results and plots saved to:", OUT_PATH)