import json
import csv
import matplotlib.pyplot as plt
from populator import NamePopulator
import numpy as np
import utils

data = utils.load_csvs_to_dicts("3 - handles merging/preprocessedData.csv")

distances = np.linspace(0,0.8, 20)
results = []
nonUniqueClusters = []
score = []

d = 0.55


pop = NamePopulator(data, k=3, maxDistanceRegister=0.8,
                    maxDistance=d,
                    maxClosenessError=1,
                    minRepetitionRate=1,
                    assumeSameCategory=True,
                    punitiveCategoryPolicy=True,
                    backTrackSplitThreshold=2.5
                    )


pop.process()

mergedMap = pop.uniqueId

data = pop.distances

#we now build the new database, from pop.distances

#for data point

output_dir = '3 - handles merging/finalData.csv'

for idx in mergedMap:
    for point in mergedMap[idx]:
        data[point]['uniqueId'] = idx
        del data[point]['dumbId']

populatedCat = 0



# now we have got to merge the categories
for idx in mergedMap:
    category = None
    counts = {}

    # count categories in the clique
    for point in mergedMap[idx]:
        point = data[point]

        if 'category_unified' not in point or point['category_unified'] is None:
            continue

        cat = point['category_unified']

        if cat not in counts:
            counts[cat] = 0

        counts[cat] += 1

    # pick most common category ONLY if any exist
    if len(counts) > 0:
        bestCount = -1
        for cat in counts:
            if counts[cat] > bestCount:
                bestCount = counts[cat]
                category = cat
    else:
        category = None  # explicit: all were None
        
        for point in mergedMap[idx]:
            point = data[point]
            point['populated_category'] = None

        continue

    # optional sanity check: print disagreements
    for point in mergedMap[idx]:
        point = data[point]

        if 'category_unified' in point:
            if point['category_unified'] != category and point['category_unified'] is not None:
                #print(category, '   ', point['category_unified'])
                aaa=0
            else:
                if point['category_unified'] is None:
                    populatedCat += 1
        else:
            populatedCat += 1

        point['populated_category'] = category



print('Populated' , populatedCat, '!!')
  

all_fields = set()

# fields you want to exclude
exclude_fields = {
    "all_id_norm",
    "belongsIn",
    "error",
    "exists",
    "handle_norm",
    "name_norm",
    "neighbors"
}

# collect all fields except excluded ones
all_fields = set()

for row in data:
    all_fields.update(k for k in row.keys() if k not in exclude_fields)

preferred_order = [
    "uniqueId",
    "handle",
    "name",
    "_platform",
    "_year",
    "_month",
    "category_unified",
    "populated_category",
    "number_videos_last_year",
    "processed_at_unix",
    "status"
]



remaining_fields = sorted(f for f in all_fields if f not in preferred_order)
fieldnames = preferred_order + remaining_fields

with open(output_dir, "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for row in data:
        clean_row = {}

        for field in fieldnames:
            value = row.get(field, "")

            # make lists / sets / dicts csv-friendly
            if isinstance(value, set):
                value = json.dumps(sorted(list(value)), ensure_ascii=False)
            elif isinstance(value, (list, dict, tuple)):
                value = json.dumps(value, ensure_ascii=False)

            clean_row[field] = value

        writer.writerow(clean_row)


