"""
1_categories_2024.py
--------------------
Fixes applied to crude_dataset/2024:
  1. Column names standardized to lowercase with underscores
  2. Each row tagged with _platform, _country, _is_global, _year
  3. TOPIC OF INFLUENCE mapped to category_unified (7 classes) via keyword rules
     Unmapped values flagged with category_status = 'UNMAPPED', kept in dataset
  4. One merged file per platform (all countries, duplicates kept)

Platforms processed: instagram, tiktok, youtube
Threads: present in raw data but excluded from this analysis (noted)

Does NOT touch: numeric string conversion (M/K suffixes), ER % strings
"""

import pandas as pd
import re
from pathlib import Path

# ============================================================
# 0. PATHS
# ============================================================
ROOT    = Path(".")
IN_DIR  = ROOT / "crude_dataset" / "2024"
OUT_DIR = ROOT / "1 - categories fixed" / "2024"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PLATFORMS = ["instagram", "tiktok", "youtube"]
# Threads is excluded — noted in script header

# ============================================================
# 1. CATEGORY RULES (2024)
#    Same 7 categories as 2022 for cross-year comparability.
#    Keyword matching used because TOPIC OF INFLUENCE is free text.
#    Priority order: specific categories first, broad ones last.
# ============================================================
CATEGORY_RULES = [
    ("Sports", [
        "sports", "sport", "soccer", "football", "basketball",
        "tennis", "racing", "fitness", "gym", "athlete", "yoga",
        "outdoor activity", "adventure", "activity",
        "ice hockey", "exercise",
    ]),
    ("Beauty&Fashion", [
        "beauty", "fashion", "modeling", "makeup", "cosmetics",
        "skincare", "self care", "hair", "accessories",
        "clothing", "luxury", "wedding", "product showcase",
        "shopping", "product presentation", "product presentations",
    ]),
    ("Knowledge&Info", [
        "news", "politics", "journalists", "journalism",
        "education", "upskilling",
        "business", "finance", "economics",
        "marketing", "advertising", "career", "careers",
        "literature", "book", "books", "author", "authors",
        "health", "medical", "society",
        "quotes", "guns", "policy",
    ]),
    ("Tech&Gaming", [
        "gaming", "video game", "video games", "video gaming",
        "games", "esports", "cosplay",
        "tech", "technology", "science", "engineering",
        "computer", "gadget", "virtualization", "automotive",
        "auto", "vehicles", "cars",
    ]),
    ("Music", [
        "music", "singer", "musician", "rapper", "songwriting",
        "band", "producers", "dance", "dancing", "dj",
        "glazba", "musik", "sica", "rap",
    ]),
    ("Entertainment", [
        "actor", "actors", "acting", "drama", "cinema",
        "movie", "movies", "film", "shows", "show", "television",
        "celebrity", "celebrities",
        "humor", "humour", "funny", "comedy", "memes",
        "animation", "entertainment", "entretenimento",
        "host", "events", "public figure", "famous", "fame",
    ]),
    ("Lifestyle", [
        "lifestyle", "life", "family", "parenting", "moms", "mothers",
        "food", "foods", "cooking", "chef", "drink",
        "travel", "trip", "trips", "travels",
        "animals", "animal", "pets", "pet",
        "photography", "photo", "nature",
        "art", "arts", "artist", "crafts", "diy",
        "home", "garden", "interior",
        "romance", "religion", "general interest",
        "children", "video blogger",
    ]),
]),
]

# ============================================================
# 2. MAPPING FUNCTION
# ============================================================
def map_topic(raw_text):
    """
    Maps a raw TOPIC OF INFLUENCE string to one of 7 unified categories.
    Returns:
        'NA'       — original value was missing
        'UNMAPPED' — has text but no keyword matched
        category   — first matching category by priority order
    """
    if pd.isna(raw_text):
        return "NA", "NA"

    # Preprocess: split camelCase, normalize separators, lowercase
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(raw_text))
    text = re.sub(r"[,/&;|]+", " ", text).lower()

    for category, keywords in CATEGORY_RULES:
        for kw in keywords:
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, text):
                return category, "MAPPED"

    return "UNMAPPED", "UNMAPPED"

# ============================================================
# 3. MAIN LOOP
# ============================================================
# Collect per-platform dataframes for merged files
platform_dfs = {p: [] for p in PLATFORMS}

mapping_report = []
all_unmapped   = []

country_dirs = sorted([d for d in IN_DIR.iterdir() if d.is_dir()])

for country_dir in country_dirs:
    country = country_dir.name
    is_global = (country == "all-countries")

    # Mirror folder structure in output
    out_country_dir = OUT_DIR / country
    out_country_dir.mkdir(parents=True, exist_ok=True)

    for platform in PLATFORMS:
        fname = f"{platform}_data_{country}.csv"
        fpath = country_dir / fname

        if not fpath.exists():
            print(f"⚠️  Missing: {fpath}")
            continue

        # --- Read ---
        try:
            df = pd.read_csv(fpath, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(fpath, encoding="latin-1")

        # --- Standardize column names ---
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace("#", "rank")
        )
        # Rename rank column if it came through as 'rank'
        if "rank" not in df.columns and df.columns[0] != "rank":
            df = df.rename(columns={df.columns[0]: "rank"})

        # If topic_of_influence missing, file was scraped in a foreign language.
        # Column order is consistent: rank, name, followers, er, country, topic, reach, [save, invite]
        # Remap by position and drop extra columns.
        if "topic_of_influence" not in df.columns:
            print(f"⚠️  Foreign language columns: {platform} {country} — remapping by position")
            df = df.iloc[:, :7]
            df.columns = ["rank", "name", "followers", "er", "country", "topic_of_influence", "potential_reach"]

        # --- Tag metadata ---
        df["_platform"]  = platform
        df["_country"]   = country
        df["_is_global"] = is_global
        df["_year"]      = 2024

        # --- Category mapping ---
        results = df["topic_of_influence"].apply(map_topic)
        df["category_unified"] = results.apply(lambda x: x[0])
        df["category_status"]  = results.apply(lambda x: x[1])

        # Collect unmapped
        unmapped_mask = df["category_status"] == "UNMAPPED"
        unmapped_vals = df.loc[unmapped_mask, "topic_of_influence"].value_counts()
        for val, count in unmapped_vals.items():
            all_unmapped.append({
                "file":         fname,
                "platform":     platform,
                "country":      country,
                "raw_topic":    val,
                "count":        count,
            })

        n_total    = len(df)
        n_mapped   = (df["category_status"] == "MAPPED").sum()
        n_na       = (df["category_status"] == "NA").sum()
        n_unmapped = (df["category_status"] == "UNMAPPED").sum()

        mapping_report.append({
            "platform":       platform,
            "country":        country,
            "n_total":        n_total,
            "n_mapped":       n_mapped,
            "n_na":           n_na,
            "n_unmapped":     n_unmapped,
            "unmapped_rate":  round(n_unmapped / n_total, 3),
        })

        # --- Save individual cleaned file ---
        out_path = out_country_dir / fname
        df.to_csv(out_path, index=False)

        platform_dfs[platform].append(df)

    print(f"✅ {country} done")

# ============================================================
# 4. SAVE MERGED FILES PER PLATFORM
# ============================================================
print("\n--- Saving merged files ---")
for platform in PLATFORMS:
    if platform_dfs[platform]:
        merged = pd.concat(platform_dfs[platform], ignore_index=True, sort=False)
        out_path = OUT_DIR / f"merged_2024_{platform}.csv"
        merged.to_csv(out_path, index=False)
        print(f"📦 {platform}: {len(merged)} rows → merged_2024_{platform}.csv")

# ============================================================
# 5. SAVE REPORTS
# ============================================================
report_df = pd.DataFrame(mapping_report)
report_df.to_csv(OUT_DIR / "mapping_report_2024.csv", index=False)

print("\n📊 Mapping quality summary (by platform):")
summary = report_df.groupby("platform")[["n_total","n_mapped","n_na","n_unmapped"]].sum()
summary["unmapped_rate"] = (summary["n_unmapped"] / summary["n_total"]).round(3)
print(summary.to_string())

if all_unmapped:
    unmapped_df = pd.DataFrame(all_unmapped).sort_values("count", ascending=False)
    unmapped_df.to_csv(OUT_DIR / "unmapped_topics_2024.csv", index=False)
    print(f"\n⚠️  Unmapped topics saved → unmapped_topics_2024.csv ({len(unmapped_df)} unique entries)")
else:
    print("\n✅ No unmapped topics found.")

