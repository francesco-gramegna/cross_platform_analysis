"""
clean_2022.py
-------------
Fixes applied to crude_dataset/kaggle_2022:
  1. Column name typos (leading/internal spaces)
  2. Missing rank column (filled from row position)
  3. instagram_june mislabeled schema (views_avg/likes_avg/comments_avg → correct names)
  4. Category mapping: category_1 → category_unified (7 classes)
     Unmapped values are kept and flagged with status = 'UNMAPPED'

Output: 1 - categories fixed/2022/
"""
import os
print("CWD:", os.getcwd())

import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# 0. PATHS
# ============================================================
ROOT   = Path(".")
IN_DIR = ROOT / "crude_dataset" / "kaggle_2022"
OUT_DIR = ROOT / "cleaned_dataset" / "1 - categories fixed" / "2022"

OUT_DIR.mkdir(parents=True, exist_ok=True)

for fpath in sorted(IN_DIR.glob("*")):
    try:
        df = pd.read_csv(fpath, encoding="utf-8")
        print(f"✅ {fpath.name}: {df.shape}")
    except Exception as e:
        print(f"❌ {fpath.name}: {e}")

# ============================================================
# 1. PER-FILE SCHEMA CORRECTIONS
#    Applied before any generic processing.
#    Keys are filenames (no extension), values are rename dicts.
# ============================================================
RENAME_FIXES = {
    # instagram_september: leading space on name_instagram
    "instagram_september": {
        " name_instagram": "name_instagram",
    },
    # tiktok_december: internal space in followers
    "tiktok_december": {
        "fo llowers": "followers",
    },
    # instagram_june: entire schema is shifted — views_avg/likes_avg/comments_avg
    # actually contain audience_country/engagement_auth/engagement_avg
    "instagram_june": {
        "views_avg":    "audience_country",
        "likes_avg":    "engagement_auth",
        "comments_avg": "engagement_avg",
    },
}

# ============================================================
# 2. CATEGORY MAP (2022)
#    Maps raw category_1 strings → 7 unified labels.
#    Any value not in this dict will be flagged UNMAPPED.
# ============================================================
CATEGORY_MAP = {
    # Entertainment
    "Cinema & Actors/actresses": "Entertainment",
    "Shows":                     "Entertainment",
    "Humor & Fun & Happiness":   "Entertainment",
    "Movies":                    "Entertainment",
    "Animation":                 "Entertainment",
    "Humor":                     "Entertainment",

    # Music
    "Music":        "Music",
    "Music & Dance":"Music",

    # Sports
    "Sports with a ball":              "Sports",
    "Sports":                          "Sports",
    "Fitness & Gym":                   "Sports",
    "Fitness":                         "Sports",
    "Racing Sports":                   "Sports",
    "Winter sports":                   "Sports",
    "Water sports":                    "Sports",
    "Extreme Sports & Outdoor activity":"Sports",

    # Beauty & Fashion
    "Beauty":                 "Beauty&Fashion",
    "Fashion":                "Beauty&Fashion",
    "Modeling":               "Beauty&Fashion",
    "Clothing & Outfits":     "Beauty&Fashion",
    "Accessories & Jewellery":"Beauty&Fashion",
    "Luxury":                 "Beauty&Fashion",

    # Tech & Gaming
    "Gaming":                  "Tech&Gaming",
    "Video games":             "Tech&Gaming",
    "Computers & Gadgets":     "Tech&Gaming",
    "Machinery & Technologies":"Tech&Gaming",
    "Science & Technology":    "Tech&Gaming",
    "Science":                 "Tech&Gaming",
    "Crypto":                  "Tech&Gaming",

    # Knowledge & Info
    "News & Politics":       "Knowledge&Info",
    "Education":             "Knowledge&Info",
    "Finance & Economics":   "Knowledge&Info",
    "Business & Careers":    "Knowledge&Info",
    "Management & Marketing":"Knowledge&Info",
    "Literature & Journalism":"Knowledge&Info",
    "Health & Self Help":    "Knowledge&Info",

    # Lifestyle
    "Lifestyle":                        "Lifestyle",
    "Daily vlogs":                      "Lifestyle",
    "Family":                           "Lifestyle",
    "Food & Cooking":                   "Lifestyle",
    "Food & Drinks":                    "Lifestyle",
    "Travel":                           "Lifestyle",
    "Animals":                          "Lifestyle",
    "Animals & Pets":                   "Lifestyle",
    "Photography":                      "Lifestyle",
    "Nature & landscapes":              "Lifestyle",
    "Art/Artists":                      "Lifestyle",
    "Design/art":                       "Lifestyle",
    "DIY & Design":                     "Lifestyle",
    "DIY & Life Hacks":                 "Lifestyle",
    "ASMR":                             "Lifestyle",
    "Toys":                             "Lifestyle",
    "Kids & Toys":                      "Lifestyle",

    # Other
    "Adult content":    "Other",
    "Cars & Motorbikes":"Other",
    "Autos & Vehicles": "Other",
    "Mystery":          "Other",
}

# ============================================================
# 3. MAIN LOOP
# ============================================================
all_dfs        = []
mapping_report = []   # per-file quality stats
all_unmapped   = []   # every unmapped raw value across all files

# Track all changes made per file for the markdown log
change_log = {}

for fpath in sorted(IN_DIR.glob("*")):
    fname = fpath.name
    change_log[fname] = []

    # --- Read ---
    try:
        df = pd.read_csv(fpath, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(fpath, encoding="latin-1")
    except Exception as e:
        print(f"❌ {fpath.name}: {type(e).__name__}: {e}")
        continue

    original_cols = df.columns.tolist()

    # --- Fix 1: per-file column renames ---
    if fname in RENAME_FIXES:
        df = df.rename(columns=RENAME_FIXES[fname])
        for old, new in RENAME_FIXES[fname].items():
            change_log[fname].append(f"Column renamed: '{old}' → '{new}'")

    # --- Fix 2: missing rank column ---
    if "rank" not in df.columns:
        df.insert(0, "rank", range(1, len(df) + 1))
        change_log[fname].append("Column added: 'rank' (filled from row position 1..n)")

    # --- Detect platform from filename ---
    fname_lower = fname.lower()
    if "instagram" in fname_lower:
        platform = "instagram"
    elif "tiktok" in fname_lower:
        platform = "tiktok"
    elif "youtube" in fname_lower:
        platform = "youtube"
    else:
        platform = "unknown"

    # --- Detect month ---
    for m in ["june", "september", "november", "december", "march"]:
        if m in fname_lower:
            month = m
            break
    else:
        month = "unknown"

    # --- Fix 3: category mapping (IG and YT only) ---
    if platform in ("instagram", "youtube") and "category_1" in df.columns:
        raw = df["category_1"].str.strip()   # strip whitespace from raw values

        mapped  = raw.map(CATEGORY_MAP)

        # Status column
        status = pd.Series("MAPPED", index=df.index, dtype=object)
        status[raw.isna()]                     = "NA"
        status[raw.notna() & mapped.isna()]    = "UNMAPPED"

        df["category_unified"] = mapped
        df["category_unified"] = df["category_unified"].where(
            status != "UNMAPPED", other="UNMAPPED"
        )
        df["category_status"]  = status

        # Collect unmapped for the report
        unmapped_vals = raw[status == "UNMAPPED"].value_counts()
        for val, count in unmapped_vals.items():
            all_unmapped.append({
                "file":     fname,
                "platform": platform,
                "month":    month,
                "raw_category": val,
                "count":    count,
            })

        change_log[fname].append(
            f"category_unified added: "
            f"{(status=='MAPPED').sum()} mapped, "
            f"{(status=='NA').sum()} NA, "
            f"{(status=='UNMAPPED').sum()} unmapped"
        )

        mapping_report.append({
            "file":           fname,
            "platform":       platform,
            "month":          month,
            "n_total":        len(df),
            "n_mapped":       (status == "MAPPED").sum(),
            "n_na":           (status == "NA").sum(),
            "n_unmapped":     (status == "UNMAPPED").sum(),
            "unmapped_rate":  round((status == "UNMAPPED").sum() / len(df), 3),
        })

    else:
        # TikTok: no category column
        change_log[fname].append("Category: skipped (no category_1 column)")

    # --- Tag metadata ---
    df["_platform"] = platform
    df["_month"]    = month
    df["_year"]     = 2022

    # --- Save individual cleaned file ---
    out_path = OUT_DIR / (fname + ".csv")
    df.to_csv(out_path, index=False)

    all_dfs.append(df)
    print(f"✅ {fname}: {len(df)} rows → saved")

# ============================================================
# 4. SAVE MERGED FILE + REPORTS
# ============================================================
merged = pd.concat(all_dfs, ignore_index=True, sort=False)
merged.to_csv(OUT_DIR / "merged_2022_all.csv", index=False)
print(f"\n📦 Merged: {len(merged)} total rows → merged_2022_all.csv")

# Mapping quality report
if mapping_report:
    report_df = pd.DataFrame(mapping_report)
    report_df.to_csv(OUT_DIR / "mapping_report_2022.csv", index=False)
    print("\n📊 Mapping quality report:")
    print(report_df.to_string(index=False))

# Unmapped values report
if all_unmapped:
    unmapped_df = pd.DataFrame(all_unmapped).sort_values("count", ascending=False)
    unmapped_df.to_csv(OUT_DIR / "unmapped_categories_2022.csv", index=False)
    print(f"\n⚠️  Unmapped categories found ({len(all_unmapped)} unique entries):")
    print(unmapped_df.to_string(index=False))
else:
    print("\n✅ No unmapped categories found.")


