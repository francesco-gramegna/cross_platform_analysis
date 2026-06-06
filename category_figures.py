# =============================================================================
# Separate category-stratified figures (December 2022, views-inclusive YouTube)
#   - category_stratified_instagram.png : Instagram Q1-Q4 median ER gap by category
#   - category_stratified_youtube.png   : YouTube Q1-Q4 median ER gap by category
# Mirrors the tier logic in rq3_analysis.py (qcut on followers, per platform).
# =============================================================================
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import mannwhitneyu

BASE      = Path(__file__).resolve().parent
# If running from inside the repo, point this at the views-inclusive file:
DATA_PATH = BASE / "4 - ER unified" / "finalData_with_er_yt_with_views.csv"
OUT_PATH  = BASE / "8 - rq3" / "plots"
OUT_PATH.mkdir(parents=True, exist_ok=True)

TIER_ORDER = ['Q1', 'Q2', 'Q3', 'Q4']
MIN_PER_TIER = 5          # require at least this many in both Q1 and Q4 to include a category
COLORS = {'instagram': '#E1306C', 'youtube': '#FF3B30'}

# ---- load + define tiers (December 2022) -----------------------------------
df = pd.read_csv(DATA_PATH, low_memory=False)
df22 = df[(df['_year'] == 2022) & (df['_month'] == 'december')].copy()
df22 = df22[df22['er_pct'].notna() & df22['followers'].notna()]
df22['tier'] = df22.groupby('_platform')['followers'].transform(
    lambda x: pd.qcut(x, q=4, labels=TIER_ORDER)
)

def category_table(platform):
    """Per-category Q1/Q4 median ER, gap, and Wilcoxon p (Q1 vs Q4)."""
    sub = df22[(df22['_platform'] == platform) & df22['category_unified'].notna()]
    rows = []
    for cat, g in sub.groupby('category_unified'):
        q1 = g[g['tier'] == 'Q1']['er_pct']
        q4 = g[g['tier'] == 'Q4']['er_pct']
        if len(q1) < MIN_PER_TIER or len(q4) < MIN_PER_TIER:
            continue
        gap = q1.median() - q4.median()
        try:
            _, p = mannwhitneyu(q1, q4, alternative='two-sided')
        except ValueError:
            p = np.nan
        rows.append({'category': cat, 'n_q1': len(q1), 'n_q4': len(q4),
                     'q1_med': q1.median(), 'q4_med': q4.median(),
                     'gap': gap, 'p': p})
    return pd.DataFrame(rows).sort_values('gap', ascending=True)  # ascending -> largest on top in barh

def plot_gap(tbl, platform, title, fname):
    fig, ax = plt.subplots(figsize=(9, 5))
    color = COLORS[platform]
    bars = ax.barh(tbl['category'], tbl['gap'], color=color, edgecolor='white')
    xmax = max(abs(tbl['gap'].max()), abs(tbl['gap'].min()), 1e-6)
    for bar, n, p in zip(bars, tbl['n_q1'] + tbl['n_q4'], tbl['p']):
        x = bar.get_width()
        star = '*' if (pd.notna(p) and p < 0.05) else 'n.s.'
        ax.text(x + 0.02 * xmax, bar.get_y() + bar.get_height() / 2,
                f"n={n}  ({star})", va='center', ha='left', fontsize=9)
    ax.margins(x=0.18)  # room for labels
    ax.axvline(0, color='black', lw=0.8)
    ax.set_xlabel('Q1 \u2212 Q4 Median ER Gap (%)')
    ax.set_title(title, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUT_PATH / fname, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"OK  {fname} saved")
    print(tbl[['category', 'n_q1', 'n_q4', 'q1_med', 'q4_med', 'gap', 'p']]
          .round(3).to_string(index=False))
    print()

ig = category_table('instagram')
yt = category_table('youtube')

plot_gap(ig, 'instagram',
         'Instagram: Micro-Influencer Advantage by Category\nDecember 2022 (* = p < 0.05)',
         'category_stratified_instagram.png')

plot_gap(yt, 'youtube',
         'YouTube: Tier Gap by Category (views-inclusive)\nDecember 2022 \u2014 no category reaches significance (n.s.)',
         'category_stratified_youtube.png')
