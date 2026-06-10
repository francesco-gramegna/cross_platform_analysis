# =============================================================================
# RQ3: Is the "micro-influencer advantage" real, and does it vary by platform?
# =============================================================================
# Data: December 2022 snapshot — Instagram, TikTok, YouTube (~1,000 per platform)
# YouTube uses views-inclusive er_pct (finalData_with_er_yt_with_views.csv)
# Robustness check confirmed: YouTube null result holds with or without views
# (F=0.66, p=0.482 in both variants)
#
# Methods:
#   1. Within-platform quartile tier definition
#   2. Permutation test (F-statistic, 10,000 shuffles) — per platform
#   3. Bootstrap 95% CI for median ER per tier x platform
#   4. Category-stratified Kruskal-Wallis + Dunn post-hoc
#   5. Temporal stability on matched creators (Instagram only)
#      a. Wilcoxon signed-rank per tier (2022 vs 2024)
#      b. Bootstrap DeltaEffect on matched Q1-Q4 gap
#
# Outputs (saved to 8 - rq3/plots/):
#   - tier_definition.png
#   - permutation_test.png
#   - bootstrap_ci_tiers.png
#   - category_stratified_instagram.png
#   - category_stratified_youtube.png
#   - temporal_matched.png
# =============================================================================

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import f_oneway, mannwhitneyu, wilcoxon, kruskal
from scikit_posthocs import posthoc_dunn

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE      = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE / "4 - ER unified" / "finalData_with_er_yt_with_views.csv"
OUT_PATH  = BASE / "8 - rq3" / "plots"
OUT_PATH.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
TIER_ORDER = ['Q1', 'Q2', 'Q3', 'Q4']
PLATFORMS  = ['instagram', 'tiktok', 'youtube']
COLORS     = {'instagram': '#E1306C', 'tiktok': '#010101', 'youtube': '#FF0000'}
B          = 10_000
SEED       = 42
x          = np.arange(4)


# =============================================================================
# LOAD DATA
# =============================================================================
df = pd.read_csv(DATA_PATH, low_memory=False)


# =============================================================================
# STEP 1 — Filter to December 2022, define within-platform quartile tiers
# =============================================================================
df22 = df[
    (df['_year'] == 2022) &
    (df['_month'] == 'december')
].copy()
df22 = df22[df22['er_pct'].notna() & df22['followers'].notna()]

df22['tier'] = df22.groupby('_platform')['followers'].transform(
    lambda x: pd.qcut(x, q=4, labels=TIER_ORDER)
)

print("── Tier counts and median ER (December 2022, YouTube views-inclusive) ──")
print(df22.groupby(['_platform', 'tier'])['er_pct'].agg(['count', 'median']).round(3))
print("\n── Follower ranges per tier ──")
print(df22.groupby(['_platform', 'tier'])['followers'].describe()[['min', '50%', 'max']].round(0))


# =============================================================================
# STEP 2 — Permutation test
# =============================================================================
def permutation_f_test(data, labels, n_permutations=B, random_state=SEED):
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

print("\n── Permutation Test Results ──")
perm_results = {}
for platform in PLATFORMS:
    sub = df22[df22['_platform'] == platform].dropna(subset=['er_pct', 'tier'])
    f_stat, p_val, perm_f = permutation_f_test(sub['er_pct'].values, sub['tier'].values)
    perm_results[platform] = {'f_stat': f_stat, 'p_val': p_val, 'perm_f': perm_f}
    p_str = "< 0.0001" if p_val == 0 else f"{p_val:.4f}"
    print(f"{platform:12s} | F = {f_stat:.2f} | p = {p_str}")


# =============================================================================
# STEP 3 — Bootstrap 95% CI for median ER
# =============================================================================
def bootstrap_median_ci(data, B=B, random_state=SEED):
    rng     = np.random.default_rng(random_state)
    medians = np.array([
        np.median(rng.choice(data, size=len(data), replace=True))
        for _ in range(B)
    ])
    return np.percentile(medians, [2.5, 97.5])

print("\n── Bootstrap 95% CI ──")
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
        print(f"{platform:12s} {tier} | median={med:.3f} | CI=[{ci_low:.3f},{ci_high:.3f}]")

ci_df = pd.DataFrame(ci_rows)


# =============================================================================
# STEP 4 — Category-stratified Kruskal-Wallis + Dunn post-hoc
# =============================================================================
print("\n── Category-Stratified Analysis ──")
cat_results_all = {}

for platform in PLATFORMS:
    print(f"\n{platform.upper()}")
    sub_plt = df22[
        (df22['_platform'] == platform) &
        df22['category_unified'].notna()
    ].copy()

    valid_cats = [
        cat for cat in sub_plt['category_unified'].unique()
        if len(sub_plt[(sub_plt['category_unified'] == cat) &
                       (sub_plt['tier'] == 'Q1')]) >= 10
        and len(sub_plt[sub_plt['category_unified'] == cat]) >= 50
    ]

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
        print(f"  {cat:20s} | n={len(sub):3d} | Q1={np.median(q1):.3f} "
              f"| Q4={np.median(q4):.3f} | gap={gap:.3f} | p={p_str}")

    cat_results_all[platform] = pd.DataFrame(cat_results)

    # Kruskal-Wallis on Q1 ER across categories
    if len(valid_cats) >= 2:
        groups = [
            sub_plt[(sub_plt['category_unified'] == cat) &
                    (sub_plt['tier'] == 'Q1')]['er_pct'].values
            for cat in valid_cats
        ]
        kw_stat, kw_p = kruskal(*groups)
        print(f"  Kruskal-Wallis (Q1 across categories): H={kw_stat:.3f}, p={kw_p:.4f}")

        if kw_p < 0.05:
            q1_data = sub_plt[
                (sub_plt['tier'] == 'Q1') &
                sub_plt['category_unified'].isin(valid_cats)
            ][['er_pct', 'category_unified']]
            dunn = posthoc_dunn(
                q1_data, val_col='er_pct',
                group_col='category_unified',
                p_adjust='bonferroni'
            )
            print("  Dunn post-hoc (Bonferroni):")
            print(dunn.round(4))


# =============================================================================
# STEP 5 — Temporal stability: matched Instagram creators
# =============================================================================
print("\n── Temporal Stability: Matched Instagram Creators ──")

ig_dec22 = df[
    (df['_platform'] == 'instagram') &
    (df['_year'] == 2022) &
    (df['_month'] == 'december')
].copy()
ig_2024 = df[
    (df['_platform'] == 'instagram') &
    (df['_year'] == 2024)
].copy()

matched_ids = set(ig_dec22['uniqueId'].dropna()) & set(ig_2024['uniqueId'].dropna())
print(f"Matched creators (Dec 2022 x 2024): {len(matched_ids)}")

ig_matched_22 = ig_dec22[ig_dec22['uniqueId'].isin(matched_ids)][
    ['uniqueId', 'er_pct', 'followers']].copy()
ig_matched_24 = ig_2024[ig_2024['uniqueId'].isin(matched_ids)][
    ['uniqueId', 'er_pct', 'followers']].copy()

matched_df = ig_matched_22.merge(
    ig_matched_24, on='uniqueId', suffixes=('_22', '_24'))
matched_df = matched_df.dropna(subset=['er_pct_22', 'er_pct_24', 'followers_22'])
matched_df['tier'] = pd.qcut(matched_df['followers_22'], q=4, labels=TIER_ORDER)
print(f"Matched pairs with complete data: {len(matched_df)}")
print(matched_df.groupby('tier')[['er_pct_22', 'er_pct_24']].median().round(3))

# 5a. Wilcoxon signed-rank per tier
print("\nWilcoxon Signed-Rank: ER change per tier")
for tier in TIER_ORDER:
    sub = matched_df[matched_df['tier'] == tier]
    stat, p = wilcoxon(sub['er_pct_22'], sub['er_pct_24'])
    direction = "decreased" if sub['er_pct_22'].median() > sub['er_pct_24'].median() else "increased"
    p_str = "< 0.0001" if p < 0.0001 else f"{p:.4f}"
    print(f"  {tier} (n={len(sub)}) | W={stat:.1f} | p={p_str} | ER {direction}")

# 5b. Bootstrap DeltaEffect
def bootstrap_delta(df_matched, B=B, random_state=SEED):
    rng    = np.random.default_rng(random_state)
    deltas = []
    for _ in range(B):
        s      = df_matched.sample(n=len(df_matched), replace=True)
        q1     = s[s['tier'] == 'Q1']
        q4     = s[s['tier'] == 'Q4']
        gap_22 = q1['er_pct_22'].median() - q4['er_pct_22'].median()
        gap_24 = q1['er_pct_24'].median() - q4['er_pct_24'].median()
        deltas.append(gap_24 - gap_22)
    deltas   = np.array(deltas)
    q1_all   = df_matched[df_matched['tier'] == 'Q1']
    q4_all   = df_matched[df_matched['tier'] == 'Q4']
    observed = (q1_all['er_pct_24'].median() - q4_all['er_pct_24'].median()) - \
               (q1_all['er_pct_22'].median() - q4_all['er_pct_22'].median())
    ci_      = np.percentile(deltas, [2.5, 97.5])
    return observed, ci_, deltas

obs, ci, boot = bootstrap_delta(matched_df)
sig = "SIGNIFICANT" if ci[0] > 0 or ci[1] < 0 else "NOT significant"
print(f"\nDeltaEffect = {obs:.3f}% | CI = [{ci[0]:.3f}, {ci[1]:.3f}]")
print(f"-> Change is {sig}")

# Follower growth check
print("\nFollower growth among matched creators:")
for tier in TIER_ORDER:
    sub    = matched_df[matched_df['tier'] == tier]
    growth = (sub['followers_24'] - sub['followers_22']) / sub['followers_22'] * 100
    print(f"  {tier} | median growth={growth.median():.1f}% | "
          f">50% grew={( growth > 50).mean()*100:.1f}%")


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
    ax.set_xticklabels(TIER_ORDER, fontsize=11)
    ax.set_yscale('log')
    ax.set_ylim(global_min, global_max)
    ax.set_ylabel('Followers (log scale)' if platform == 'instagram' else '')
    ax.set_title(platform.capitalize(), fontweight='bold', fontsize=13)
    ax.grid(axis='y', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

fig.suptitle(
    'Follower Range per Tier × Platform (December 2022)\n'
    'Bar = min-max range  ·  dot = median',
    fontweight='bold', fontsize=13
)
plt.tight_layout()
plt.savefig(OUT_PATH / 'tier_definition.png', bbox_inches='tight', dpi=150)
plt.close()
print("\n✅ Plot 1: tier_definition.png")


# ── Plot 2: Permutation test ──────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(14, 4))

for ax, platform in zip(axes, PLATFORMS):
    res    = perm_results[platform]
    obs_f  = res['f_stat']
    perm_f = res['perm_f']
    p_val  = res['p_val']
    p_str  = "p < 0.0001" if p_val == 0 else f"p = {p_val:.4f}"

    # Clip x-axis at 99.5th percentile — observed F annotated if off-axis
    clip         = np.percentile(perm_f, 99.5)
    perm_clipped = perm_f[perm_f <= clip]

    ax.hist(perm_clipped, bins=60, color=COLORS[platform],
            alpha=0.6, edgecolor='white')
    ax.set_xlim(0, clip)
    ax.set_xlabel('F-statistic (permuted)')
    ax.set_ylabel('Frequency')
    ax.set_title(platform.capitalize(), fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if obs_f <= clip:
        ax.axvline(obs_f, color='black', linewidth=2,
                   label=f'Observed F = {obs_f:.1f}')
        ax.legend(fontsize=8)
    else:
        ax.annotate(
            f'Observed F = {obs_f:.1f}\n(off axis →)',
            xy=(clip, ax.get_ylim()[1] * 0.5),
            xytext=(clip * 0.55, ax.get_ylim()[1] * 0.72),
            fontsize=9, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='black'),
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
        )

    ax.text(0.97, 0.97, p_str,
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
print("✅ Plot 2: permutation_test.png")


# ── Plot 3: Bootstrap CI ──────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=False)

for ax, platform in zip(axes, PLATFORMS):
    sub      = ci_df[ci_df['platform'] == platform]
    medians  = sub['median'].values
    err_low  = medians - sub['ci_low'].values
    err_high = sub['ci_high'].values - medians
    ax.errorbar(x, medians, yerr=[err_low, err_high],
                fmt='o-', color=COLORS[platform],
                capsize=5, linewidth=2, markersize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(TIER_ORDER)
    ax.set_title(platform.capitalize(), fontsize=13, fontweight='bold')
    ax.set_xlabel('Follower Tier')
    ax.set_ylabel('Median ER (%)')
    ax.grid(axis='y', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

fig.suptitle(
    'Median ER by Follower Tier (December 2022)\n'
    'Bootstrap 95% CI  ·  y-axes scaled independently per platform',
    fontsize=13, fontweight='bold', y=1.02
)
plt.tight_layout()
plt.savefig(OUT_PATH / 'bootstrap_ci_tiers.png', bbox_inches='tight', dpi=150)
plt.close()
print("✅ Plot 3: bootstrap_ci_tiers.png")


# ── Plot 4: Category-stratified (2 panels: Instagram + YouTube) ──────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

ig_cat_df     = cat_results_all['instagram'].sort_values('q1_med', ascending=True)
ig_cat_df_gap = cat_results_all['instagram'].sort_values('gap', ascending=True)

# Instagram Q1 median
ax = axes[0, 0]
ax.barh(ig_cat_df['category'], ig_cat_df['q1_med'],
        color='#E1306C', alpha=0.7, edgecolor='#E1306C')
ax.set_xlabel('Q1 Median ER (%)')
ax.set_title('Instagram: Q1 Median ER by Category\nKW H=12.865, p=0.012',
             fontweight='bold', fontsize=11)
ax.grid(axis='x', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
for _, row in ig_cat_df.iterrows():
    idx = list(ig_cat_df['category']).index(row['category'])
    ax.text(row['q1_med'] + 0.1, idx, f"n={row['n']}", va='center', fontsize=9)

# Instagram Q1-Q4 gap
ax = axes[0, 1]
ax.barh(ig_cat_df_gap['category'], ig_cat_df_gap['gap'],
        color='#E1306C', alpha=0.7, edgecolor='#E1306C')
ax.set_xlabel('Q1 − Q4 Median ER Gap (%)')
ax.set_title('Instagram: Q1−Q4 Gap by Category\nKW H=12.865, p=0.012',
             fontweight='bold', fontsize=11)
ax.grid(axis='x', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
for _, row in ig_cat_df_gap.iterrows():
    idx = list(ig_cat_df_gap['category']).index(row['category'])
    ax.text(row['gap'] + 0.1, idx, f"n={row['n']}", va='center', fontsize=9)

# YouTube
yt_cat  = cat_results_all.get('youtube', pd.DataFrame())

if not yt_cat.empty:
    yt_cat_df     = yt_cat.sort_values('q1_med', ascending=True)
    yt_cat_df_gap = yt_cat.sort_values('gap', ascending=True)
    colors_yt     = ['#FF4444' if cat == 'Tech&Gaming' else '#FF0000'
                     for cat in yt_cat_df['category']]
    colors_yt_gap = ['#FF4444' if cat == 'Tech&Gaming' else '#FF0000'
                     for cat in yt_cat_df_gap['category']]

    # YouTube Q1 median
    ax = axes[1, 0]
    ax.barh(yt_cat_df['category'], yt_cat_df['q1_med'],
            color=colors_yt, alpha=0.7, edgecolor='#FF0000')
    ax.set_xlabel('Q1 Median ER (%)')
    ax.set_title('YouTube: Q1 Median ER by Category\nKW H=18.993, p=0.001',
                 fontweight='bold', fontsize=11)
    ax.grid(axis='x', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for _, row in yt_cat_df.iterrows():
        idx = list(yt_cat_df['category']).index(row['category'])
        ax.text(row['q1_med'] + 0.001, idx, f"n={row['n']}", va='center', fontsize=9)

    # YouTube Q1-Q4 gap
    ax = axes[1, 1]
    ax.barh(yt_cat_df_gap['category'], yt_cat_df_gap['gap'],
            color=colors_yt_gap, alpha=0.7, edgecolor='#FF0000')
    ax.axvline(0, color='black', linewidth=0.8)
    ax.set_xlabel('Q1 − Q4 Median ER Gap (%)')
    ax.set_title('YouTube: Q1−Q4 Gap by Category\nKW H=18.993, p=0.001',
                 fontweight='bold', fontsize=11)
    ax.grid(axis='x', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for _, row in yt_cat_df_gap.iterrows():
        idx = list(yt_cat_df_gap['category']).index(row['category'])
        offset = 0.001 if row['gap'] >= 0 else -0.001
        ha     = 'left' if row['gap'] >= 0 else 'right'
        ax.text(row['gap'] + offset, idx, f"n={row['n']}",
                va='center', fontsize=9, ha=ha)

fig.suptitle('Category-Stratified Analysis (December 2022)',
             fontweight='bold', fontsize=14)
plt.tight_layout()
plt.savefig(OUT_PATH / 'category_stratified.png', bbox_inches='tight', dpi=150)
plt.close()
print("✅ Plot 4: category_stratified.png")


# ── Plot 5: Temporal matched creators ────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Left: tier ER 2022 vs 2024
ax    = axes[0]
x4    = np.arange(4)
med22 = [matched_df[matched_df['tier'] == t]['er_pct_22'].median() for t in TIER_ORDER]
med24 = [matched_df[matched_df['tier'] == t]['er_pct_24'].median() for t in TIER_ORDER]

ax.plot(x4, med22, 'o-',  color='#E1306C', linewidth=2, markersize=7, label='2022')
ax.plot(x4, med24, 'o--', color='#880E4F', linewidth=2, markersize=7, label='2024')
ax.set_xticks(x4)
ax.set_xticklabels(TIER_ORDER)
ax.set_xlabel('Follower Tier (defined by 2022 followers)')
ax.set_ylabel('Median ER (%)')
ax.set_title(f'Instagram: Matched Creators\nTier ER by Year (n={len(matched_df)})',
             fontweight='bold')
ax.legend()
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Right: bootstrap DeltaEffect
ax = axes[1]
ax.hist(boot, bins=80, color='#E1306C', alpha=0.7, edgecolor='white')
ax.axvline(obs,   color='black', linewidth=2,   label=f'ΔEffect = {obs:.2f}%')
ax.axvline(ci[0], color='gray',  linestyle='--', linewidth=1.5, label='95% CI')
ax.axvline(ci[1], color='gray',  linestyle='--', linewidth=1.5)
ax.axvline(0,     color='red',   linestyle=':',  linewidth=1.5, label='Zero (no change)')
ax.set_xlabel('ΔEffect (2024 − 2022)')
ax.set_ylabel('Frequency')
ax.set_title('Bootstrap Distribution of ΔEffect\n(Matched Instagram Q1−Q4 gap change)',
             fontweight='bold')
ax.legend(fontsize=8)
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig(OUT_PATH / 'temporal_matched.png', bbox_inches='tight', dpi=150)
plt.close()
print("✅ Plot 5: temporal_matched.png")

print(f"\n✅ All done. Plots saved to: {OUT_PATH}")
