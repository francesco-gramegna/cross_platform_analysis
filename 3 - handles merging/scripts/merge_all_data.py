import csv

input_dir = "2 - countries and numbers fixed"

fileOut = "3 - handles merging/preprocessedData.csv"


data = []

#Youtube

data2022 = []


def get_single_value(row, keys, field_name):
    values = [row[k] for k in keys if row.get(k) and row[k].strip()]

    if len(values) == 0:
        return None
    if len(values) > 1:
        raise ValueError(f"Multiple {field_name}s found in row: {values}")

    return values[0]


#load youtube and unify the handles and names

with open(input_dir + '/2022/merged_2022_all.csv', 'r') as file:
    reader = csv.DictReader(file)

    for row in reader:
        handle_keys = ["handle_instagram", "handle_tiktok", "handle_youtube"]
        name_keys = ["name_instagram", "name_tiktok", "name_youtube"]

        # Create unified fields
        row["handle"] = get_single_value(row, handle_keys, "handles")
        row["name"] = get_single_value(row, name_keys, "names")

        # Remove old fields
        for key in handle_keys + name_keys:
            row.pop(key, None)

        data2022.append(row)


#nontrivial duplication check
deduped = {}
deletecounter = 0

def has_category(row):
    val = row.get("category_unified")
    return val is not None and str(val).strip() != ""

def get_followers(row):
    return float(row["followers"]) if row.get("followers") not in (None, "") else 0

for row in data2022:
    key = (row["handle"], row["_month"], row["_year"], row["_platform"])

    if key not in deduped:
        deduped[key] = row
    else:
        existing = deduped[key]

        # Prefer the one with category_unified
        if has_category(row) and not has_category(existing):
            deduped[key] = row
        elif has_category(existing) and not has_category(row):
            pass  # keep existing
        else:
            # fallback: compare followers
            if get_followers(row) > get_followers(existing):
                deduped[key] = row

        print(row['handle'])
        deletecounter += 1

data2022 = list(deduped.values())

for row in data2022:
    del row['rank']



print('deleted ', deletecounter)


#===== 2024 ====

def load_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def split_name_handle(row):
    raw = row.get("name", "") or ""

    if "@" in raw:
        name_part, handle_part = raw.rsplit("@", 1)  # split on LAST @
        row["name"] = name_part.strip()
        row["handle"] = handle_part.strip().replace("@", "")
    else:
        row["name"] = raw.strip()
        row["handle"] = None  # or "" if you prefer

    return row


data1 = load_csv(input_dir + "/2024/merged_2024_instagram.csv")
data2 = load_csv(input_dir+ "/2024/merged_2024_youtube.csv")
data3 = load_csv(input_dir+"/2024/merged_2024_tiktok.csv")

# --- Combine ---
data2024 = data1 + data2 + data3

# --- Process rows ---
for row in data2024:
    split_name_handle(row)


# issue : duplication for global and not global  e e

#Brutal solution : should not loose any info : remove any global row

buf = []

glob = set()
for row in data2024:
    del row['rank']
    if row['_is_global'] == 'True':
        glob.add(row['handle'])

for row in data2024:
    if row['_is_global'] == 'False':
        if row['handle'] not in glob:
            buf.append(row)
    else:
        buf.append(row)


data2024 = buf



# ---- 2026

data2026 = load_csv(input_dir + '/2026/2026_youtube.csv')

for row in data2026:
    del row['status']
    del row['error']

    del row['processed_at_unix']

    if 'handle_youtube' in row:
        row['handle'] = row['handle_youtube']
        del row['handle_youtube']
    if 'name_youtube' in row:
        row['name'] = row['name_youtube']
        del row['name_youtube']



data = data2022+data2024+data2026

keys = set()

for row in data:
    key = row.keys()
    keys.update(key)




#unionize the keys
FIELD_MAP = {
    "avg_likes": "likes_avg",
    "avg_views": "views_avg",
    "avg_comments": "comments_avg",
}

for row in data:
    for old_key, new_key in FIELD_MAP.items():
        if old_key in row:
            old_val = row.get(old_key)
            new_val = row.get(new_key)

            # Only overwrite if new_key is missing or empty,
            # and do not copy placeholder zero values into the unified field
            if (new_key not in row or new_val in (None, "")) and old_val not in (None, "", "0", 0):
                row[new_key] = old_val

            # Remove the old key
            del row[old_key]

keys = set()

for row in data:
    key = row.keys()
    keys.update(key)

print(keys)

#now we write the csv

preferred_order = [
    "handle",
    "name",
    "_platform",
    "_year",
    "_month",
    "category_unified",
]

# --- collect all keys ---
all_keys = set()
for row in data:
    all_keys.update(row.keys())

# --- build final column order ---
remaining_keys = [k for k in all_keys if k not in preferred_order]
fieldnames = preferred_order + sorted(remaining_keys)

# --- write to CSV ---
with open(fileOut, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)

    writer.writeheader()
    writer.writerows(data)
