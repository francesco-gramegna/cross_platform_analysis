"""
translate_and_remap_2024.py
---------------------------
Translates non-English TOPIC OF INFLUENCE strings from affected files
to English using deep-translator (Google Translate), then re-applies
category mapping on all files and rebuilds merged platform files.

11 files were scraped with a non-English UI. Columns were remapped by
position in 1_categories_2024.py, but topic content remained in the
original language. This script handles the translation step.

Additionally, Estonian strings from instagram_united-kingdom were not
caught by the initial translation pass and were corrected manually.

Methodology: "Non-English topic fields translated via Google Translate
(deep-translator) prior to category mapping. Mistranslations identified
during unmapped review were corrected manually. Category assignment uses
the same keyword rules uniformly across all files and years."

Output:
  - topic_translations_2024.csv  — full translation lookup table
  - Re-saved individual cleaned files with corrected category columns
  - Updated merged_2024_{platform}.csv for instagram, tiktok, youtube
"""

import pandas as pd
import re
import time
from pathlib import Path
from deep_translator import GoogleTranslator

# ============================================================
# 0. PATHS
# ============================================================
ROOT    = Path(".")
OUT_DIR = ROOT / "1 - categories fixed" / "2024"

AFFECTED = [
    ("belgium",              "tiktok"),
    ("brazil",               "instagram"),
    ("czechia",              "youtube"),
    ("finland",              "youtube"),
    ("indonesia",            "tiktok"),
    ("morocco",              "youtube"),
    ("poland",               "tiktok"),
    ("romania",              "instagram"),
    ("sweden",               "tiktok"),
    ("united-arab-emirates", "instagram"),
    ("united-kingdom",       "youtube"),
    ("united-kingdom",       "instagram"),  # Estonian strings
]

PLATFORMS = ["instagram", "tiktok", "youtube"]

# ============================================================
# 1. CATEGORY RULES (final — same as 1_categories_2024.py)
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
]

def map_topic(raw_text):
    if pd.isna(raw_text):
        return "NA", "NA"
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(raw_text))
    text = re.sub(r"[,/&;|]+", " ", text).lower()
    for category, keywords in CATEGORY_RULES:
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                return category, "MAPPED"
    return "UNMAPPED", "UNMAPPED"

# ============================================================
# 2. COLLECT UNIQUE TOPICS FROM AFFECTED FILES
# ============================================================
all_topics = set()
for country, platform in AFFECTED:
    fpath = OUT_DIR / country / f"{platform}_data_{country}.csv"
    if not fpath.exists():
        print(f"⚠️  Missing: {fpath}")
        continue
    df = pd.read_csv(fpath)
    topics = df["topic_of_influence"].dropna().unique()
    all_topics.update(topics)

unique_topics = sorted(all_topics)
print(f"Total unique topics to translate: {len(unique_topics)}")

# ============================================================
# 3. TRANSLATE VIA GOOGLE TRANSLATE (deep-translator)
# ============================================================
def translate_topic(text):
    try:
        result = GoogleTranslator(source="auto", target="en").translate(text)
        return result if result else text
    except Exception:
        return text

translation_map = {}
print(f"Translating {len(unique_topics)} topics...")
for i, topic in enumerate(unique_topics):
    translation_map[topic] = translate_topic(topic)
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(unique_topics)} done...")
    time.sleep(0.1)
print("✅ Translation complete")

# Save translation table
trans_df = pd.DataFrame([{"original": k, "english": v} for k, v in translation_map.items()])
trans_df.to_csv(OUT_DIR / "topic_translations_2024.csv", index=False, encoding="utf-8")
print(f"💾 Translation table saved: {len(trans_df)} entries")

# ============================================================
# 4. RE-APPLY MAPPING TO AFFECTED FILES
# ============================================================
print("\nRe-mapping affected files...")
for country, platform in AFFECTED:
    fpath = OUT_DIR / country / f"{platform}_data_{country}.csv"
    if not fpath.exists():
        continue
    df = pd.read_csv(fpath)
    df["topic_of_influence_en"] = df["topic_of_influence"].map(
        lambda x: translation_map.get(x, x) if pd.notna(x) else x
    )
    results = df["topic_of_influence_en"].apply(map_topic)
    df["category_unified"] = results.apply(lambda x: x[0])
    df["category_status"]  = results.apply(lambda x: x[1])
    df.to_csv(fpath, index=False)
    n_mapped   = (df["category_status"] == "MAPPED").sum()
    n_unmapped = (df["category_status"] == "UNMAPPED").sum()
    n_na       = (df["category_status"] == "NA").sum()
    print(f"✅ {platform} {country}: {n_mapped} mapped, {n_unmapped} unmapped, {n_na} NA")

# ============================================================
# 5. REBUILD MERGED FILES
# ============================================================
print("\nRebuilding merged files...")
trans_df = pd.read_csv(OUT_DIR / "topic_translations_2024.csv")
translation_map = dict(zip(trans_df["original"], trans_df["english"]))

for platform in PLATFORMS:
    dfs = []
    for country_dir in sorted([d for d in OUT_DIR.iterdir() if d.is_dir()]):
        fpath = country_dir / f"{platform}_data_{country_dir.name}.csv"
        if fpath.exists():
            dfs.append(pd.read_csv(fpath))
    if dfs:
        merged = pd.concat(dfs, ignore_index=True, sort=False)
        merged["topic_of_influence_en"] = merged["topic_of_influence"].map(
            lambda x: translation_map.get(x, x) if pd.notna(x) else x
        )
        results = merged["topic_of_influence_en"].apply(map_topic)
        merged["category_unified"] = results.apply(lambda x: x[0])
        merged["category_status"]  = results.apply(lambda x: x[1])
        merged.to_csv(OUT_DIR / f"merged_2024_{platform}.csv", index=False)
        n_mapped   = (merged["category_status"] == "MAPPED").sum()
        n_na       = (merged["category_status"] == "NA").sum()
        n_unmapped = (merged["category_status"] == "UNMAPPED").sum()
        print(f"📦 {platform}: {len(merged)} rows — mapped: {n_mapped}, NA: {n_na}, unmapped: {n_unmapped}")
