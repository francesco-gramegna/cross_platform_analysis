"""
2_countries_and_numbers.py
--------------------------
Fixes applied to 1 - categories fixed/ outputs:

2022:
  - Coalesces 'country' and 'audience_country' → single 'audience_country' column
  - Replaces '-' with NaN in country column
  - Converts numeric string columns (M/K suffixes) to float

2024:
  - Renames 'country' → 'audience_country'
  - Converts ER column: '-' → NaN, strips '%', converts to float

2026:
  - Converts 2-letter ISO codes → full country names in 'country' → 'audience_country'
  - Numeric columns already clean

Output: 2 - countries and numbers fixed/{year}/
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path

# ============================================================
# 0. PATHS
# ============================================================
ROOT     = Path(".")
IN_2022  = ROOT / "1 - categories fixed" / "2022"
IN_2024  = ROOT / "1 - categories fixed" / "2024"
IN_2026  = ROOT / "1 - categories fixed" / "2026"
OUT_2022 = ROOT / "2 - countries and numbers fixed" / "2022"
OUT_2024 = ROOT / "2 - countries and numbers fixed" / "2024"
OUT_2026 = ROOT / "2 - countries and numbers fixed" / "2026"

for d in [OUT_2022, OUT_2024, OUT_2026]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# 1. ISO CODE → COUNTRY NAME MAP (2026)
# ============================================================
ISO_MAP = {
    "AE": "United Arab Emirates",
    "AR": "Argentina",
    "AT": "Austria",
    "AU": "Australia",
    "BR": "Brazil",
    "CA": "Canada",
    "CH": "Switzerland",
    "CL": "Chile",
    "CO": "Colombia",
    "DE": "Germany",
    "EC": "Ecuador",
    "EG": "Egypt",
    "ES": "Spain",
    "FR": "France",
    "GB": "United Kingdom",
    "ID": "Indonesia",
    "IE": "Ireland",
    "IN": "India",
    "IQ": "Iraq",
    "IT": "Italy",
    "JO": "Jordan",
    "JP": "Japan",
    "KR": "South Korea",
    "KW": "Kuwait",
    "MX": "Mexico",
    "MY": "Malaysia",
    "NL": "Netherlands",
    "NO": "Norway",
    "PE": "Peru",
    "PH": "Philippines",
    "PK": "Pakistan",
    "PS": "Palestine",
    "QA": "Qatar",
    "RU": "Russia",
    "SA": "Saudi Arabia",
    "SE": "Sweden",
    "TH": "Thailand",
    "TR": "Turkey",
    "UA": "Ukraine",
    "US": "United States",
    "VE": "Venezuela",
    "VN": "Vietnam",
}

# ============================================================
# 2. NUMERIC CONVERSION HELPERS
# ============================================================
def parse_metric(val):
    """
    Converts strings like '409.8M', '30.8K', '5' to float.
    Returns NaN for missing, '-', or unparseable values.
    """
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if s in ("", "-", "N/A", "n/a"):
        return np.nan
    s = s.replace(",", "")
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if s.upper().endswith(suffix):
            try:
                return float(s[:-1]) * mult
            except ValueError:
                return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan

def parse_er(val):
    """
    Converts ER strings like '1.09%', '0.01%' to float (as percentage, e.g. 1.09).
    Returns NaN for '-' or missing.
    """
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if s in ("", "-", "N/A"):
        return np.nan
    s = s.replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan

# ============================================================
# 3. PROCESS 2022
# ============================================================
print("=" * 50)
print("Processing 2022...")
print("=" * 50)

NUMERIC_COLS_2022 = {
    "instagram": ["followers", "engagement_auth", "engagement_avg"],
    "tiktok":    ["followers", "views_avg", "likes_avg", "comments_avg", "shares_avg"],
    "youtube":   ["followers", "views_avg", "likes_avg", "comments_avg"],
}

files_2022 = [f for f in IN_2022.glob("*.csv") if not f.name.startswith("merged") and not f.name.startswith("mapping")]

for fpath in sorted(files_2022):
    fname = fpath.name
    df = pd.read_csv(fpath)

    # --- Country: coalesce country + audience_country → audience_country ---
    if "country" in df.columns and "audience_country" in df.columns:
        df["audience_country"] = df["audience_country"].combine_first(df["country"])
        df = df.drop(columns=["country"])
    elif "country" in df.columns:
        df = df.rename(columns={"country": "audience_country"})

    # Replace '-' with NaN in audience_country
    if "audience_country" in df.columns:
        df["audience_country"] = df["audience_country"].replace("-", np.nan)

    # --- Numeric conversion ---
    platform = df["_platform"].iloc[0] if "_platform" in df.columns else "unknown"
    num_cols = NUMERIC_COLS_2022.get(platform, [])
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_metric)

    out_path = OUT_2022 / fname
    df.to_csv(out_path, index=False)
    print(f"✅ {fname}")

# Rebuild merged 2022
all_dfs = [pd.read_csv(f) for f in sorted(OUT_2022.glob("*.csv")) if not f.name.startswith("merged")]
merged = pd.concat(all_dfs, ignore_index=True, sort=False)
merged.to_csv(OUT_2022 / "merged_2022_all.csv", index=False)
print(f"\n📦 2022 merged: {len(merged)} rows")

# ============================================================
# 4. PROCESS 2024
# ============================================================
print("\n" + "=" * 50)
print("Processing 2024...")
print("=" * 50)

# Process individual country files
country_dirs = sorted([d for d in IN_2024.iterdir() if d.is_dir()])
PLATFORMS_2024 = ["instagram", "tiktok", "youtube"]

for country_dir in country_dirs:
    country = country_dir.name
    out_country_dir = OUT_2024 / country
    out_country_dir.mkdir(parents=True, exist_ok=True)

    for platform in PLATFORMS_2024:
        fname = f"{platform}_data_{country}.csv"
        fpath = country_dir / fname
        if not fpath.exists():
            continue

        df = pd.read_csv(fpath)

        # Rename country → audience_country
        if "country" in df.columns:
            df = df.rename(columns={"country": "audience_country"})

        # Convert numeric columns
        for col in ["followers", "potential_reach"]:
            if col in df.columns:
                df[col] = df[col].apply(parse_metric)

        # Convert ER
        if "er" in df.columns:
            df["er"] = df["er"].apply(parse_er)

        df.to_csv(out_country_dir / fname, index=False)

    print(f"✅ {country}")

# Rebuild merged 2024 per platform
print("\nRebuilding 2024 merged files...")
for platform in PLATFORMS_2024:
    dfs = []
    for country_dir in sorted([d for d in OUT_2024.iterdir() if d.is_dir()]):
        fpath = country_dir / f"{platform}_data_{country_dir.name}.csv"
        if fpath.exists():
            dfs.append(pd.read_csv(fpath))
    if dfs:
        merged = pd.concat(dfs, ignore_index=True, sort=False)
        merged.to_csv(OUT_2024 / f"merged_2024_{platform}.csv", index=False)
        print(f"📦 {platform}: {len(merged)} rows")

# ============================================================
# 5. PROCESS 2026
# ============================================================
print("\n" + "=" * 50)
print("Processing 2026...")
print("=" * 50)

df26 = pd.read_csv(IN_2026 / "2026_youtube.csv")

# Convert ISO codes → full country names, rename to audience_country
df26["audience_country"] = df26["country"].map(ISO_MAP)

# Flag any codes not in the map
unmapped_codes = df26[df26["audience_country"].isna() & df26["country"].notna()]["country"].unique()
if len(unmapped_codes) > 0:
    print(f"⚠️  Unmapped ISO codes: {unmapped_codes}")

df26 = df26.drop(columns=["country"])

df26.to_csv(OUT_2026 / "2026_youtube.csv", index=False)
print(f"✅ 2026_youtube.csv: {len(df26)} rows")
print(f"   audience_country filled: {df26['audience_country'].notna().sum()}")
print(f"   audience_country NA: {df26['audience_country'].isna().sum()}")

# ============================================================
# 6. QUALITY CHECK
# ============================================================
print("\n" + "=" * 50)
print("Quality check — audience_country sample per year")
print("=" * 50)

for label, path in [
    ("2022", OUT_2022 / "merged_2022_all.csv"),
    ("2024 instagram", OUT_2024 / "merged_2024_instagram.csv"),
    ("2026", OUT_2026 / "2026_youtube.csv"),
]:
    df = pd.read_csv(path)
    print(f"\n--- {label} ---")
    print(df["audience_country"].value_counts().head(5))
    