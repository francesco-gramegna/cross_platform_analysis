"""
Figure Generation Script for Raw Data Description Section
==========================================================
Generates all 6 figures used in Section II of the midterm report.

Inputs (must be placed in scripts/eda_output/):
    - follower_raw.csv         : raw follower values per record
    - er_dist_2024.csv         : raw ER values for 2024 dataset
    - country_values_2022_2026.csv : country column values (2022 + 2026)
    - category_top.csv         : top category labels per source
    - numeric_fields_raw.csv   : raw numeric engagement fields
    - raw_data_summary.csv     : per-file metadata for missingness heatmap

Outputs (written to scripts/figures/):
    - fig1_follower.png        : follower distribution by source
    - fig2_er_2024.png         : 2024 raw ER distribution by platform
    - fig3_country.png         : country distribution (2022 + 2026)
    - fig4_categories.png      : top category labels (3-source comparison)
    - fig5_numeric.png         : raw numeric engagement field distributions
    - fig6_missingness.png    : per-slice missingness heatmap

Usage:
    cd ~/Documents/projects/cross_platform_analysis
    python scripts/generate_figures.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.gridspec import GridSpec
from pathlib import Path

# ============================================================
# Paths
# ============================================================
SCRIPT_DIR = Path(__file__).parent
EDA_DIR = SCRIPT_DIR / "eda_output"
OUT_DIR = SCRIPT_DIR / "figures"
OUT_DIR.mkdir(exist_ok=True)

# ============================================================
# Common style
# ============================================================
plt.rcParams['font.family'] = 'DejaVu Sans'

# Color palette: light/medium/dark blue for the three sources,
# with green reserved for 2026 (the scraped source)
COLORS = {
    'Kaggle 2022':        '#9ecae1',
    '2024 Multi-Country': '#4292c6',
    '2026 YouTube':       '#08519c',
}


# ============================================================
# Figure 1 — Follower distribution by data source
# ============================================================
def make_fig1_follower():
    """Histogram of follower counts (log scale), one color per source."""
    df = pd.read_csv(EDA_DIR / "follower_raw.csv")
    df = df[df['followers'] > 0]

    fig, ax = plt.subplots(figsize=(7, 3.5))

    for src in ['Kaggle 2022', '2024 Multi-Country', '2026 YouTube']:
        sub = df[df['source'] == src]
        foll = sub['followers']
        if len(foll) == 0:
            continue
        ax.hist(np.log10(foll), bins=40, alpha=0.55,
                label=f"{src} (N={len(foll):,}, median={foll.median()/1e6:.1f}M)",
                color=COLORS[src], edgecolor='white', linewidth=0.5)

    ax.set_xlabel('Followers (log scale)', fontsize=10)
    ax.set_ylabel('Count', fontsize=10)
    ax.set_title('Follower distribution by data source (raw data)', fontsize=11)

    # Convert log10 ticks to readable follower counts (1K, 10K, ...)
    ticks = [3, 4, 5, 6, 7, 8, 9]
    labels = ['1K', '10K', '100K', '1M', '10M', '100M', '1B']
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=9)

    ax.legend(fontsize=9, frameon=False, loc='upper left')
    for s in ['top', 'right']:
        ax.spines[s].set_visible(False)
    ax.grid(axis='y', linestyle=':', alpha=0.4)

    plt.tight_layout()
    plt.savefig(OUT_DIR / 'fig1_follower.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  fig1_follower.png")


# ============================================================
# Figure 2 — 2024 raw ER distribution by platform
# ============================================================
def make_fig2_er_2024():
    """Boxplot of raw ER values for the 2024 dataset, by platform."""
    df = pd.read_csv(EDA_DIR / "er_dist_2024.csv")
    # Truncate extreme outliers so the boxplot is readable
    df = df[(df['er_value'] >= 0) & (df['er_value'] <= 200)]

    fig, ax = plt.subplots(figsize=(6.5, 3.6))

    platform_colors = {
        'instagram': '#9ecae1',
        'youtube':   '#4292c6',
        'tiktok':    '#08519c',
    }
    order = ['instagram', 'youtube', 'tiktok']
    labels = ['Instagram', 'YouTube', 'TikTok']

    groups = [df[df['platform'] == plat]['er_value'].values for plat in order]

    bp = ax.boxplot(groups, tick_labels=labels, patch_artist=True,
                    showfliers=False, widths=0.5,
                    medianprops={'color': 'black', 'linewidth': 1.5})
    for patch, plat in zip(bp['boxes'], order):
        patch.set_facecolor(platform_colors[plat])
        patch.set_alpha(0.85)
        patch.set_edgecolor('#333')

    # Median labels above the median line; sample size below the box
    for i, (g, plat, lab) in enumerate(zip(groups, order, labels)):
        if len(g) > 0:
            med = np.median(g)
            ax.text(i + 1, med + 0.3, f"{med:.2f}%", ha='center', fontsize=9,
                    color='#222', fontweight='bold')
            ax.text(i + 1, -1.0, f"N={len(g):,}", ha='center', fontsize=8,
                    color='#666', style='italic')

    ax.set_ylim(-1.8, 8)
    ax.set_ylabel('Engagement rate (raw ER field, %)', fontsize=10)
    ax.set_title('Raw ER distribution in the 2024 dataset, by platform', fontsize=11)
    ax.tick_params(axis='x', labelsize=10)
    ax.tick_params(axis='y', labelsize=9)
    ax.grid(axis='y', linestyle=':', alpha=0.4)
    for s in ['top', 'right']:
        ax.spines[s].set_visible(False)

    # Annotation: 2022 and 2026 do not have an ER field at all
    ax.text(0.99, 0.97,
            'Kaggle 2022 and 2026 YouTube raw\nfiles do not contain an ER field;\nER must be reconstructed.',
            transform=ax.transAxes, ha='right', va='top',
            fontsize=8.5, style='italic', color='#555',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#f5f5f5', edgecolor='none'))

    plt.tight_layout()
    plt.savefig(OUT_DIR / 'fig2_er_2024.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  fig2_er_2024.png")


# ============================================================
# Figure 3 — Country distribution (2022 + 2026)
# ============================================================
def make_fig3_country():
    """
    Two-panel bar chart of the country column for Kaggle 2022 and 2026.
    The 2024 source is excluded because country is encoded in the file
    structure, not in a column (this is mentioned in the figure caption).
    """
    df = pd.read_csv(EDA_DIR / "country_values_2022_2026.csv")

    fig = plt.figure(figsize=(7.5, 4))
    gs = GridSpec(1, 2, figure=fig, wspace=1.4,
                  left=0.13, right=0.97, top=0.78, bottom=0.18)

    # --- Left panel: Kaggle 2022 (Instagram + YouTube combined) ---
    ax = fig.add_subplot(gs[0])
    sub = df[df['source'] == 'Kaggle 2022']
    top = sub['country'].value_counts().head(10).sort_values()
    ax.barh(np.arange(len(top)), top.values, color='#4292c6', edgecolor='white')
    ax.set_yticks(np.arange(len(top)))
    ax.set_yticklabels(top.index, fontsize=8.5)
    for i, v in enumerate(top.values):
        ax.text(v + top.max() * 0.02, i, str(v), va='center',
                fontsize=8, color='#333')
    ax.set_xlim(0, top.max() * 1.15)
    ax.set_xlabel('Records', fontsize=9)
    for s in ['top', 'right']:
        ax.spines[s].set_visible(False)
    ax.tick_params(axis='x', labelsize=7.5)
    ax.grid(axis='x', linestyle=':', alpha=0.3)

    pos = ax.get_position()
    fig.text((pos.x0 + pos.x1) / 2, 0.92, 'Kaggle 2022 (Instagram + YouTube)',
             ha='center', fontsize=10, fontweight='bold')
    fig.text((pos.x0 + pos.x1) / 2, 0.86,
             f'N={len(sub):,}; TikTok 2022 has no country field',
             ha='center', fontsize=8, style='italic', color='#555')

    # --- Right panel: 2026 YouTube ---
    ax = fig.add_subplot(gs[1])
    sub = df[df['source'] == '2026 YouTube']
    top = sub['country'].value_counts().head(10).sort_values()
    ax.barh(np.arange(len(top)), top.values, color='#74c476', edgecolor='white')
    ax.set_yticks(np.arange(len(top)))
    ax.set_yticklabels(top.index, fontsize=8.5)
    for i, v in enumerate(top.values):
        ax.text(v + top.max() * 0.02, i, str(v), va='center',
                fontsize=8, color='#333')
    ax.set_xlim(0, top.max() * 1.15)
    ax.set_xlabel('Records', fontsize=9)
    for s in ['top', 'right']:
        ax.spines[s].set_visible(False)
    ax.tick_params(axis='x', labelsize=7.5)
    ax.grid(axis='x', linestyle=':', alpha=0.3)

    pos = ax.get_position()
    fig.text((pos.x0 + pos.x1) / 2, 0.92, '2026 YouTube',
             ha='center', fontsize=10, fontweight='bold')
    fig.text((pos.x0 + pos.x1) / 2, 0.86,
             f'N={len(sub):,}; uses ISO codes (US, IN, ...)',
             ha='center', fontsize=8, style='italic', color='#555')

    # Footnote at the bottom: explain why 2024 is not shown
    fig.text(0.5, 0.04,
             'The 2024 dataset is organized by country (60 country folders + 1 all-countries aggregate);',
             ha='center', va='top', fontsize=8, style='italic', color='#555')
    fig.text(0.5, 0.005,
             'country information there is encoded in the file structure, not in a column.',
             ha='center', va='top', fontsize=8, style='italic', color='#555')

    plt.savefig(OUT_DIR / 'fig3_country.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  fig3_country.png")


# ============================================================
# Figure 4 — Top category labels by source
# ============================================================
def make_fig4_categories():
    """
    Three-panel bar chart of top category labels for each data source.
    Demonstrates that the three sources use three different labelling
    philosophies: fixed taxonomy, free-text, Wikipedia-style.
    """
    df = pd.read_csv(EDA_DIR / "category_top.csv")
    # Drop NaN entries from the top labels list
    # (these are records with missing category in the raw data)
    df = df[df['label'].notna()].copy()

    TOP_N = 10

    fig = plt.figure(figsize=(8.5, 4.7))
    gs = GridSpec(1, 3, figure=fig, wspace=1.5,
                  left=0.13, right=0.98, top=0.78, bottom=0.13)

    def make_panel(ax, src, color, title, subtitle):
        sub = df[df['source'] == src].head(TOP_N).sort_values('count', ascending=True)
        if len(sub) == 0:
            return
        ax.barh(np.arange(len(sub)), sub['count'].values,
                color=color, edgecolor='white')
        ax.set_yticks(np.arange(len(sub)))
        ax.set_yticklabels(sub['label'].tolist(), fontsize=8)
        for i, v in enumerate(sub['count'].values):
            ax.text(v + sub['count'].max() * 0.02, i, str(v),
                    va='center', fontsize=7.5, color='#333')
        ax.set_xlim(0, sub['count'].max() * 1.20)
        for s in ['top', 'right']:
            ax.spines[s].set_visible(False)
        ax.tick_params(axis='x', labelsize=7)
        ax.grid(axis='x', linestyle=':', alpha=0.3)
        # Title / subtitle placed via figure-level text to avoid overlap
        pos = ax.get_position()
        fig.text((pos.x0 + pos.x1) / 2, 0.93, title,
                 ha='center', fontsize=10.5, fontweight='bold')
        fig.text((pos.x0 + pos.x1) / 2, 0.88, subtitle,
                 ha='center', fontsize=8.5, style='italic', color='#555')

    # Source-level metadata is duplicated per row in category_top.csv;
    # take the first row of each source group to read total_unique etc.
    full = pd.read_csv(EDA_DIR / "category_top.csv")
    kaggle_info = full[full['source'] == 'Kaggle 2022'].iloc[0]
    m24_info = full[full['source'] == '2024 Multi-Country'].iloc[0]
    yt26_info = full[full['source'] == '2026 YouTube'].iloc[0]
    once_pct_24 = m24_info['appear_once_count'] / m24_info['total_unique'] * 100

    make_panel(fig.add_subplot(gs[0]), 'Kaggle 2022', '#9ecae1',
               'Kaggle 2022',
               f'fixed taxonomy: {int(kaggle_info["total_unique"])} labels')
    make_panel(fig.add_subplot(gs[1]), '2024 Multi-Country', '#4292c6',
               '2024 Multi-Country',
               f'free text: {int(m24_info["total_unique"]):,} unique strings')
    make_panel(fig.add_subplot(gs[2]), '2026 YouTube', '#74c476',
               '2026 YouTube',
               f'Wikipedia-style: {int(yt26_info["total_unique"])} labels')

    fig.text(0.5, 0.04,
             f'In 2024, {once_pct_24:.0f}% of unique strings appear only once '
             '— most are concatenations of multiple labels.',
             ha='center', va='bottom', fontsize=8.5, style='italic', color='#444')

    plt.savefig(OUT_DIR / 'fig4_categories.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  fig4_categories.png")


# ============================================================
# Figure 5 — Distribution of raw numeric engagement fields
# ============================================================
def make_fig5_numeric():
    """
    Six-panel grid showing the distribution of each numeric engagement
    field on a log10 scale. Only Kaggle 2022 and 2026 YouTube provide
    these fields; the 2024 source aggregates them into a single ER value.
    """
    df = pd.read_csv(EDA_DIR / "numeric_fields_raw.csv")
    df = df[df['value'] > 0]

    field_order = ['likes_avg', 'comments_avg', 'views_avg', 'shares_avg',
                   'engagement_auth', 'engagement_avg']
    field_titles = {
        'likes_avg':       'likes (per-post avg)',
        'comments_avg':    'comments (per-post avg)',
        'views_avg':       'views (per-post avg)',
        'shares_avg':      'shares (per-post avg)',
        'engagement_auth': 'engagement_auth (count)',
        'engagement_avg':  'engagement_avg (count)',
    }
    source_colors = {'Kaggle 2022': '#4292c6', '2026 YouTube': '#74c476'}

    fig, axes = plt.subplots(2, 3, figsize=(8.5, 5.4))
    axes = axes.flatten()

    for i, field in enumerate(field_order):
        ax = axes[i]
        sub = df[df['field'] == field]
        if len(sub) == 0:
            ax.axis('off')
            continue

        sources_present = sub['source'].unique()
        for src in ['Kaggle 2022', '2026 YouTube']:
            if src not in sources_present:
                continue
            ssub = sub[sub['source'] == src]
            log_v = np.log10(ssub['value'])
            ax.hist(log_v, bins=30, alpha=0.6, color=source_colors[src],
                    edgecolor='white', linewidth=0.4,
                    label=f"{src.split()[0]} (N={len(ssub):,})")

        # Build "median:" annotation embedded in the x-axis label
        medians = sub.groupby('source')['value'].median()
        median_lines = []
        for src in ['Kaggle 2022', '2026 YouTube']:
            if src in medians.index:
                v = medians[src]
                v_str = f"{v/1e3:.0f}K" if v < 1e6 else f"{v/1e6:.1f}M"
                median_lines.append(f"{src.split()[0]}={v_str}")
        median_text = "median: " + ", ".join(median_lines)

        ax.set_title(field_titles[field], fontsize=10, fontweight='bold')
        ax.set_xlabel(f'log10 — {median_text}', fontsize=8.5)
        if i in [0, 3]:
            ax.set_ylabel('Count', fontsize=8.5)

        ax.legend(fontsize=7.5, frameon=False, loc='upper left')
        ax.tick_params(axis='both', labelsize=7.5)
        for s in ['top', 'right']:
            ax.spines[s].set_visible(False)
        ax.grid(axis='y', linestyle=':', alpha=0.3)

    fig.suptitle('Per-post numeric engagement fields (raw): only Kaggle 2022 and 2026 YouTube provide them',
                 fontsize=10.5, y=1.0)
    fig.text(0.5, -0.01,
             '2024 raw files do not expose per-post averages — only an aggregated ER value (Fig. 2).',
             ha='center', va='top', fontsize=8.5, style='italic', color='#555')

    plt.tight_layout()
    plt.savefig(OUT_DIR / 'fig5_numeric.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  fig5_numeric.png")


# ============================================================
# Figure 6 — Per-slice missingness heatmap
# ============================================================
def make_fig6_missingness():
    """
    Heatmap of missingness rates (string sentinels included) for the
    four key fields across the seven slice (year x platform) combinations.
    Grey cells mark fields entirely absent from the source schema.
    """
    df = pd.read_csv(SCRIPT_DIR / "raw_data_summary.csv")

    def make_slice_label(row):
        f = row['file']
        if f.startswith('kaggle_2022'):
            plat = f.split('/')[-1].split('_')[0]
            return f"2022 {plat.capitalize()}"
        elif f.startswith('2024'):
            plat = f.split('/')[-1].split('_')[0]
            if plat == 'threads':  # excluded from analysis
                return None
            return f"2024 {plat.capitalize()}"
        elif f.startswith('2026'):
            return "2026 YouTube"
        return None

    df['slice'] = df.apply(make_slice_label, axis=1)
    df = df[df['slice'].notna()].copy()

    # Aggregate missingness across files within each slice (record-weighted)
    def agg_slice(g):
        w = g['n_records']
        def wmean_or_na(col):
            if g[col].isna().all():
                return np.nan
            return (g[col].fillna(0) * w).sum() / w.sum()
        return pd.Series({
            'category':  wmean_or_na('category_null_pct'),
            'country':   wmean_or_na('country_null_pct'),
            'ER':        wmean_or_na('er_null_pct'),
            'followers': wmean_or_na('followers_null_pct'),
        })

    agg = df.groupby('slice').apply(agg_slice)

    # Display order (group by year)
    order = ['2022 Instagram', '2022 Youtube', '2022 Tiktok',
             '2024 Instagram', '2024 Youtube', '2024 Tiktok',
             '2026 YouTube']
    agg = agg.loc[[x for x in order if x in agg.index]]

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    heat_cols = ['category', 'country', 'ER', 'followers']
    heat = agg[heat_cols].values

    cmap = mpl.cm.Reds.copy()
    cmap.set_bad(color='#e8e8e8')  # fields absent from schema -> grey
    heat_masked = np.ma.masked_invalid(heat)

    im = ax.imshow(heat_masked, cmap=cmap, vmin=0, vmax=100, aspect='auto')

    # Cell annotations: percentage with bold style for high-missingness cells
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            v = heat[i, j]
            if np.isnan(v):
                ax.text(j, i, 'absent', ha='center', va='center',
                        color='#777', fontsize=9, style='italic')
            else:
                color = 'white' if v > 55 else '#222'
                weight = 'bold' if v > 50 else 'normal'
                ax.text(j, i, f"{v:.1f}%", ha='center', va='center',
                        color=color, fontsize=9.5, fontweight=weight)

    ax.set_xticks(range(len(heat_cols)))
    ax.set_xticklabels(['Category', 'Country', 'ER', 'Followers'], fontsize=10)
    ax.set_yticks(range(len(agg)))
    ax.set_yticklabels(agg.index.tolist(), fontsize=10)

    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.tick_params(length=0)

    cbar = plt.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
    cbar.set_label('% missing', fontsize=9)
    cbar.ax.tick_params(labelsize=8)
    cbar.outline.set_visible(False)

    # White separator lines between year groups
    if len(agg) >= 6:
        ax.axhline(2.5, color='white', lw=2.5)
        ax.axhline(5.5, color='white', lw=2.5)

    plt.tight_layout()
    plt.savefig(OUT_DIR / 'fig6_missingness.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  fig6_missingness.png")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print(f"Reading inputs from: {EDA_DIR}")
    print(f"Writing figures to:  {OUT_DIR}\n")
    print("Generated:")

    make_fig1_follower()
    make_fig2_er_2024()
    make_fig3_country()
    make_fig4_categories()
    make_fig5_numeric()
    make_fig6_missingness()

    print(f"\nAll 6 figures saved to {OUT_DIR}")
