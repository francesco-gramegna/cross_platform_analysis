import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

raw_path = '/Users/draco/Desktop/2026 Spring/DS516/project/cross_platform_analysis/crude_dataset/kaggle_2022/'
months = ['march', 'june', 'september', 'november', 'december']
month_labels = ['Mar', 'Jun', 'Sep', 'Nov', 'Dec']
PALETTE = {"Instagram": "#C13584", "YouTube": "#FF0000", "TikTok": "#010101"}

configs = [
    ('Instagram', 'instagram', 'handle_instagram'),
    ('YouTube',   'youtube',   'handle_youtube'),
    ('TikTok',    'tiktok',    'handle_tiktok'),
]

appearance_data = {}
for plat, folder, col in configs:
    frames = [pd.read_csv(raw_path + f'{folder}_{m}')[[col]] for m in months]
    all_h = pd.concat(frames)[col].dropna().str.lower().str.strip()
    appearance_data[plat] = all_h.value_counts()

fig, axes = plt.subplots(1, 2, figsize=(16, 6.5))
fig.subplots_adjust(top=0.92, bottom=0.12, left=0.07, right=0.97, wspace=0.35)

# ── LEFT: grouped bar ─────────────────────────────────────────────────────────
ax = axes[0]
categories = ['Only once\n(1 month)', 'Occasional\n(2–4 months)', 'Consistent\n(all 5 months)']
bar_positions = np.arange(3)
width = 0.22

for i, (plat, _, _) in enumerate(configs):
    counts = appearance_data[plat]
    total  = len(counts)
    vals   = [
        (counts == 1).sum() / total * 100,
        ((counts >= 2) & (counts <= 4)).sum() / total * 100,
        (counts == 5).sum() / total * 100,
    ]
    color = PALETTE[plat]
    bars = ax.bar(bar_positions + i*width, vals, width,
                  label=plat, color=color, alpha=0.88, edgecolor='white')
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + 0.5,
                f'{v:.0f}%', ha='center', va='bottom',
                fontsize=8, fontweight='bold', color=color)

ax.set_xticks(bar_positions + width)
ax.set_xticklabels(categories, fontsize=10)
ax.set_ylabel('% of unique accounts', fontsize=11)
ax.set_ylim(0, 78)
ax.set_title('How Long Did Each Account Stay\nin the Top 1,000?', fontweight='bold', fontsize=12)
ax.legend(fontsize=9, loc='upper right')

ax.annotate('TikTok: 41% appear\nonly once',
            xy=(0 + 2*width, 41), xytext=(0.55, 60),
            xycoords=('data', 'data'), textcoords=('data', 'data'),
            fontsize=8.5, color=PALETTE['TikTok'], fontweight='bold',
            arrowprops=dict(arrowstyle='->', color=PALETTE['TikTok'], lw=1.5))

# ── RIGHT: overlap per month ───────────────────────────────────────────────────
ax2 = axes[1]
x_pos = np.arange(len(months))

all_overlaps = {}
for plat, folder, col in configs:
    sets = {m: set(pd.read_csv(raw_path + f'{folder}_{m}')[col]
                     .dropna().str.lower().str.strip())
            for m in months}
    overlaps = [None] + [
        len(sets[m1] & sets[m2]) / len(sets[m1] | sets[m2]) * 100
        for m1, m2 in zip(months, months[1:])
    ]
    all_overlaps[plat] = overlaps

max_val = max(v for vals in all_overlaps.values() for v in vals if v is not None)

for plat, folder, col in configs:
    overlaps = all_overlaps[plat]
    color = PALETTE[plat]
    xs = x_pos[1:]
    ys = overlaps[1:]
    ax2.plot(xs, ys, marker='o', color=color,
             linewidth=2.5, markersize=8, label=plat)
    for x, y in zip(xs, ys):
        va = 'bottom' if plat != 'TikTok' else 'top'
        offset = 1.5 if plat != 'TikTok' else -1.5
        ax2.text(x, y + offset, f'{y:.0f}%', ha='center', va=va,
                 fontsize=8.5, color=color, fontweight='bold')

ax2.set_xticks(x_pos[1:])
ax2.set_xticklabels(month_labels[1:], fontsize=11)
ax2.set_ylabel('Jaccard overlap with previous month (%)', fontsize=11)
ax2.set_ylim(0, max_val + 12)
ax2.set_title('How Stable Is the Top 1,000\nMonth-to-Month?', fontweight='bold', fontsize=12)
ax2.legend(fontsize=9, loc='lower right')
ax2.set_xlabel('Month (2022)', fontsize=11)

out = '/Users/draco/Desktop/2026 Spring/DS516/project/cross_platform_analysis/Exploratory data analysis/rq1_figures/tiktok_ranking_volatility.png'
plt.savefig(out, dpi=150, bbox_inches='tight')
plt.close()
print('Saved:', out)
