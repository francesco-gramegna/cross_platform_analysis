"""
1_categories_2026.py
--------------------
Fixes applied to crude_dataset/2026/2026:
  1. category mapped to category_unified (7 classes)
     Unmapped values kept and flagged with category_status = 'UNMAPPED'
  2. Row tagged with _platform = 'youtube', _year = 2026
  3. File saved with .csv extension

YouTube only — no Instagram or TikTok in 2026 data.
Numeric columns already clean (no M/K suffixes).
Country is 2-letter ISO code — standardization deferred.

Output: 1 - categories fixed/2026/2026_youtube.csv
"""

import pandas as pd
from pathlib import Path

# ============================================================
# 0. PATHS
# ============================================================
ROOT    = Path(".")
IN_FILE = ROOT / "crude_dataset" / "2026" / "2026"
OUT_DIR = ROOT / "1 - categories fixed" / "2026"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 1. CATEGORY MAP (2026)
#    Wikipedia-style labels → 7 unified categories
# ============================================================
CATEGORY_MAP_2026 = {
    # Entertainment
    "Entertainment":    "Entertainment",
    "Film":             "Entertainment",
    "Television program": "Entertainment",
    "Humour":           "Entertainment",
    "Performing arts":  "Entertainment",

    # Music
    "Pop music":             "Music",
    "Music":                 "Music",
    "Music of Asia":         "Music",
    "Electronic music":      "Music",
    "Hip hop music":         "Music",
    "Music of Latin America":"Music",
    "Soul music":            "Music",
    "Christian music":       "Music",
    "Independent music":     "Music",

    # Sports
    "Sport":               "Sports",
    "Association football": "Sports",
    "Mixed martial arts":  "Sports",
    "Physical fitness":    "Sports",
    "Motorsport":          "Sports",

    # Tech & Gaming
    "Role-playing video game":   "Tech&Gaming",
    "Action game":               "Tech&Gaming",
    "Action-adventure game":     "Tech&Gaming",
    "Video game culture":        "Tech&Gaming",
    "Simulation video game":     "Tech&Gaming",
    "Casual game":               "Tech&Gaming",
    "Technology":                "Tech&Gaming",
    "Racing video game":         "Tech&Gaming",

    # Knowledge & Info
    "Society":   "Knowledge&Info",
    "Politics":  "Knowledge&Info",
    "Knowledge": "Knowledge&Info",
    "Religion":  "Knowledge&Info",
    "Health":    "Knowledge&Info",

    # Lifestyle
    "Lifestyle (sociology)": "Lifestyle",
    "Hobby":                 "Lifestyle",
    "Food":                  "Lifestyle",
    "Tourism":               "Lifestyle",
    "Pet":                   "Lifestyle",
}

# ============================================================
# 2. LOAD & MAP
# ============================================================
try:
    df = pd.read_csv(IN_FILE, encoding="utf-8")
except UnicodeDecodeError:
    df = pd.read_csv(IN_FILE, encoding="latin-1")

print(f"Loaded: {df.shape[0]} rows, {df.shape[1]} columns")

raw    = df["category"]
mapped = raw.map(CATEGORY_MAP_2026)

status = pd.Series("MAPPED", index=df.index, dtype=object)
status[raw.isna()]                  = "NA"
status[raw.notna() & mapped.isna()] = "UNMAPPED"

df["category_unified"] = mapped.where(status == "MAPPED", other=status)
df["category_status"]  = status
df["_platform"]        = "youtube"
df["_year"]            = 2026

# ============================================================
# 3. QUALITY REPORT
# ============================================================
n_mapped   = (status == "MAPPED").sum()
n_na       = (status == "NA").sum()
n_unmapped = (status == "UNMAPPED").sum()

print(f"\n📊 Mapping quality:")
print(f"   Mapped:   {n_mapped} ({n_mapped/len(df):.1%})")
print(f"   NA:       {n_na} ({n_na/len(df):.1%})")
print(f"   Unmapped: {n_unmapped} ({n_unmapped/len(df):.1%})")

if n_unmapped > 0:
    print(f"\n⚠️  Unmapped categories:")
    print(df[status == "UNMAPPED"]["category"].value_counts().to_string())

print(f"\n📊 category_unified distribution:")
print(df["category_unified"].value_counts().to_string())

# ============================================================
# 4. SAVE
# ============================================================
out_path = OUT_DIR / "2026_youtube.csv"
df.to_csv(out_path, index=False)
print(f"\n✅ Saved: {out_path} ({len(df)} rows)")
