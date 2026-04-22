from tqdm import tqdm
import matplotlib.pyplot as plt
from populator import NamePopulator
import numpy as np
import utils
import itertools

data = utils.load_csvs_to_dicts("cleaned_dataset/updated/*")

distances = np.linspace(0, 0.8, 20)

#grid except maxDistanceRegister
grid_k = [3]
grid_maxClosenessError = [1,2]
grid_minRepetitionRate = [0, 0.5, 1]
grid_assumeSameCategory = [True]
grid_punitiveCategoryPolicy = [True, False]
grid_backTrackSplitThreshold = [1.5, 2, 2.5]

allResults = []

for k, maxClosenessError, minRepetitionRate, assumeSameCategory, punitiveCategoryPolicy, backTrackSplitThreshold in tqdm(itertools.product(
    grid_k,
    grid_maxClosenessError,
    grid_minRepetitionRate,
    grid_assumeSameCategory,
    grid_punitiveCategoryPolicy,
    grid_backTrackSplitThreshold
)):

    results = []
    nonUniqueClusters = []
    score = []

    print("Testing :",
          "k =", k,
          "| maxClosenessError =", maxClosenessError,
          "| minRepetitionRate =", minRepetitionRate,
          "| assumeSameCategory =", assumeSameCategory,
          "| punitiveCategoryPolicy =", punitiveCategoryPolicy,
          "| backTrackSplitThreshold =", backTrackSplitThreshold)

    for d in distances:
        pop = NamePopulator(
            data,
            k=k,
            maxDistanceRegister=0.8,
            maxDistance=d,
            maxClosenessError=maxClosenessError,
            minRepetitionRate=minRepetitionRate,
            assumeSameCategory=assumeSameCategory,
            punitiveCategoryPolicy=punitiveCategoryPolicy,
            backTrackSplitThreshold=backTrackSplitThreshold,
            verbose=False
        )

        pop.process()

        results.append(pop.getAverageDiameter(pop.uniqueId, 2))

        non_unique = len(pop.getNonSingleClusters())
        total_clusters = len(pop.uniqueId.keys())
        nonUniqueClusters.append(non_unique / total_clusters if total_clusters > 0 else 0)

        score.append(pop.getMeanClosestClusterDistanceFromGraph(pop.uniqueId))

    peakIdx = int(np.argmax(score))
    peakScore = score[peakIdx]
    peakDistance = distances[peakIdx]
    mostUniqueScore = nonUniqueClusters[peakIdx]
    avgDiameterAtPeak = results[peakIdx]

    allResults.append({
        'params': {
            'k': k,
            'maxClosenessError': maxClosenessError,
            'minRepetitionRate': minRepetitionRate,
            'assumeSameCategory': assumeSameCategory,
            'punitiveCategoryPolicy': punitiveCategoryPolicy,
            'backTrackSplitThreshold': backTrackSplitThreshold
        },
        'peakIdx': peakIdx,
        'peakDistance': peakDistance,
        'peakScore': peakScore,
        'mostUniqueScore': mostUniqueScore,
        'avgDiameterAtPeak': avgDiameterAtPeak,
        'scoreCurve': score,
        'diameterCurve': results,
        'nonUniqueCurve': nonUniqueClusters
    })

#rank:
#1) highest peak score
#2) highest mostUniqueScore at that peak
#3) lowest diameter at peak
allResults = sorted(
    allResults,
    key=lambda x: (-x['peakScore'], -x['mostUniqueScore'], x['avgDiameterAtPeak'])
)

print("\n\n========== TOP 5 COMBINATIONS ==========\n")

for i, r in enumerate(allResults[:5]):
    p = r['params']

    print("Rank", i+1)
    print("params :",
          "k =", p['k'],
          "| maxClosenessError =", p['maxClosenessError'],
          "| minRepetitionRate =", p['minRepetitionRate'],
          "| assumeSameCategory =", p['assumeSameCategory'],
          "| punitiveCategoryPolicy =", p['punitiveCategoryPolicy'],
          "| backTrackSplitThreshold =", p['backTrackSplitThreshold'])

    print("peakDistance :", r['peakDistance'])
    print("peakScore :", r['peakScore'])
    print("mostUniqueScore at peak :", r['mostUniqueScore'])
    print("avgDiameterAtPeak :", r['avgDiameterAtPeak'])
    print("")


best = allResults[0]
print("========== BEST COMBINATION ==========")
print(best['params'])
print("peakDistance :", best['peakDistance'])
print("peakScore :", best['peakScore'])
print("mostUniqueScore at peak :", best['mostUniqueScore'])
print("avgDiameterAtPeak :", best['avgDiameterAtPeak'])

#optional: plot best curves
fig, ax1 = plt.subplots()

ax1.plot(distances, best['diameterCurve'], 'b-o', label="Avg diameter")
ax1.set_xlabel("maxDistance")
ax1.set_ylabel("Avg diameter", color='b')

ax2 = ax1.twinx()
ax2.plot(distances, best['scoreCurve'], 'r-o', label="Score")
ax2.set_ylabel("Score", color='r')

plt.title("Best parameter combination")
plt.grid(True)
plt.show()
