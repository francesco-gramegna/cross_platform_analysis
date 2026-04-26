"""
Step 6: Top-1,000 ranking volatility (2022 monthly snapshots only)

Input:  4 - ER unified/finalData_with_er.csv
Output: 6 - tiktok volatility/plots/tiktok_ranking_volatility.png
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
SRC  = ROOT / "4 - ER unified" / "finalData_with_er.csv"
OUT  = ROOT / "6 - tiktok volatility" / "plots"
OUT.mkdir(exist_ok=True, parents=True)

months       = ["march", "june", "september", "november", "december"]
month_labels = ["Mar", "Jun", "Sep", "Nov", "Dec"]
PALETTE = {"Instagram": "#C13584", "YouTube": "#FF0000", "TikTok": "#010101"}
PLATFORMS = [("Instagram", "instagram"), ("YouTube", "youtube"), ("TikTok", "tiktok")]

df = pd.read_csv(SRC, low_memory=False)
df22 = df[df["_year"] == 2022].copy()
df22["handle"] = df22["handle"].astype(str).str.lower().str.strip()

# (platform → {month → set of handles}) and (platform → handle appearance counts)
month_sets, appearance_data = {}, {}
for label, key in PLATFORMS:
    sub = df22[df22["_platform"] == key]
    sets = {m: set(sub.loc[sub["_month"] == m, "handle"].dropna()) for m in months}
    month_sets[label] = sets
    all_h = pd.concat([pd.Series(list(s)) for s in sets.values()])
    appearance_data[label] = all_h.value_counts()

fig, axes = plt.subplots(1, 2, figsize=(16, 6.5))
fig.subplots_adjust(top=0.92, bottom=0.12, left=0.07, right=0.97, wspace=0.35)

# ── LEFT: persistence buckets ───────────────────────────────────────────────
ax = axes[0]
categories = ["Only once\n(1 month)", "Occasional\n(2–4 months)", "Consistent\n(all 5 months)"]
bar_pos = np.arange(3)
width = 0.22

for i, (label, _) in enumerate(PLATFORMS):
    counts = appearance_data[label]
    total  = len(counts)
    vals = [
        (counts == 1).sum() / total * 100,
        ((counts >= 2) & (counts <= 4)).sum() / total * 100,
        (counts == 5).sum() / total * 100,
    ]
    color = PALETTE[label]
    bars = ax.bar(bar_pos + i * width, vals, width,
                  label=label, color=color, alpha=0.88, edgecolor="white")
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{v:.0f}%", ha="center", va="bottom",
                fontsize=8, fontweight="bold", color=color)

ax.set_xticks(bar_pos + width)
ax.set_xticklabels(categories, fontsize=10)
ax.set_ylabel("% of unique accounts", fontsize=11)
ax.set_ylim(0, 78)
ax.set_title("How Long Did Each Account Stay\nin the Top 1,000?",
             fontweight="bold", fontsize=12)
ax.legend(fontsize=9, loc="upper right")

tt_only_once = (appearance_data["TikTok"] == 1).sum() / len(appearance_data["TikTok"]) * 100
ax.annotate(f"TikTok: {tt_only_once:.0f}% appear\nonly once",
            xy=(0 + 2 * width, tt_only_once), xytext=(0.55, 60),
            fontsize=8.5, color=PALETTE["TikTok"], fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=PALETTE["TikTok"], lw=1.5))

# ── RIGHT: month-to-month Jaccard overlap ───────────────────────────────────
ax2 = axes[1]
x_pos = np.arange(len(months))

all_overlaps = {}
for label, _ in PLATFORMS:
    sets = month_sets[label]
    overlaps = [None] + [
        len(sets[m1] & sets[m2]) / len(sets[m1] | sets[m2]) * 100
        for m1, m2 in zip(months, months[1:])
    ]
    all_overlaps[label] = overlaps

max_val = max(v for vals in all_overlaps.values() for v in vals if v is not None)

for label, _ in PLATFORMS:
    overlaps = all_overlaps[label]
    color = PALETTE[label]
    xs = x_pos[1:]
    ys = overlaps[1:]
    ax2.plot(xs, ys, marker="o", color=color, linewidth=2.5, markersize=8, label=label)
    for x, y in zip(xs, ys):
        va = "bottom" if label != "TikTok" else "top"
        offset = 1.5 if label != "TikTok" else -1.5
        ax2.text(x, y + offset, f"{y:.0f}%", ha="center", va=va,
                 fontsize=8.5, color=color, fontweight="bold")

ax2.set_xticks(x_pos[1:])
ax2.set_xticklabels(month_labels[1:], fontsize=11)
ax2.set_ylabel("Jaccard overlap with previous month (%)", fontsize=11)
ax2.set_ylim(0, max_val + 12)
ax2.set_title("How Stable Is the Top 1,000\nMonth-to-Month?",
              fontweight="bold", fontsize=12)
ax2.legend(fontsize=9, loc="lower right")
ax2.set_xlabel("Month (2022)", fontsize=11)

out_path = OUT / "tiktok_ranking_volatility.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {out_path}")
