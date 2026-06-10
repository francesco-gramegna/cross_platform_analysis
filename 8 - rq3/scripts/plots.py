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
    # In the permutation test plot, for instagram specifically:
    if platform == 'instagram':
        ax.set_xscale('linear')  # remove log scale
        ax.set_xlim(0, 5)
        ax.set_xlabel('F-statistic (permuted)')
        ax.text(4.8, ax.get_ylim()[1]*0.85, 
            f'Observed F = {obs_f:.1f}\n(off-axis →)',
            ha='right', va='top', fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    # Remove the vertical line since it's off-axis
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
    'with Bootstrap 95% CI',
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