import json
import csv
import matplotlib.pyplot as plt
from populator import NamePopulator
import numpy as np
import utils

data = utils.load_csvs_to_dicts("cleaned_dataset/updated/*")

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

output_dir = 'cleaned_dataset/final/all_merged.csv'

for idx in mergedMap:
    for point in mergedMap[idx]:
        print(point)
        data[point]['uniqueId'] = idx
        del data[point]['dumbId']


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


