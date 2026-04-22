import matplotlib.pyplot as plt
from populator import NamePopulator
import numpy as np
import utils

data = utils.load_csvs_to_dicts("cleaned_dataset/updated/*")

distances = np.linspace(0,0.8, 20)
results = []
nonUniqueClusters = []
score = []

distances = [0.70]

pop = NamePopulator(data, k=3, maxDistanceRegister=0.8,
                    maxDistance=0.6,
                    maxClosenessError=2,
                    minRepetitionRate=1,
                    assumeSameCategory=True,
                    punitiveCategoryPolicy=True,
                    backTrackSplitThreshold=2             
                    )


pop.process()



official = 0
total = 0
for d in data:
    if 'handle' in d and d['handle'] != None:
        total += 1
        if(len(str(d['handle'])) == 25):
           print(d['handle'])
    if 'name' in d and d['name'] != None:
        total +=1
        if 'official' in str(d['name']).lower():
            official+=1

print(official)
print(total)

