import os
from tqdm import tqdm
import bisect
import re
import numpy as np
from plottings import plot_unique_id_size_distribution, plot_cluster_size_distribution
import matplotlib.pyplot as plt
import utils
import json


#softer normalisation
def normalizeString(s):
    if s is None:
        return []
    s = str(s)

    toRemove = ["official", "tiktok", "instagram", "youtube"]

    s = s.lower().strip()

    for x in toRemove:
        s = s.replace(x, '')

    # keep all letters/digits from any language, plus spaces
    s = ''.join(c for c in s if c.isalnum() or c == ' ')

    # collapse repeated spaces
    s = ' '.join(s.split())

    return s.split(' ') if s else []



class NamePopulator():

    def __init__(self, data, k=3, maxDistanceRegister = 0.8 , maxDistance=0.8, maxClosenessError=2, minRepetitionRate=0, assumeSameCategory=True, punitiveCategoryPolicy=True, backTrackSplitThreshold=2, verbose=True):
        self.data = data
        self.k = k
        self.path = 'temp/distances.csv'
        self.maxDistanceRegister = maxDistanceRegister
        self.maxDistance = maxDistance
        self.maxClosenessError = maxClosenessError
        self.minRepetitionRate = minRepetitionRate

        self.assumeSameCategory=assumeSameCategory
        self.punitiveCategoryPolicy=punitiveCategoryPolicy

        self.backTrackSplitThreshold = backTrackSplitThreshold
        self.verbose = verbose

    
    def save_full_data(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

        if self.verbose:
                print(f"Full dataset saved to {self.path}")

    def load_full_data(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def createDistances(self):
        
        counter = 0
        for x in self.data:
            x['dumbId'] = counter
            counter += 1

            x['handle_norm'] = normalizeString(x['handle'])
            x['name_norm'] = normalizeString(x['name'])
            x['all_id_norm'] =  x['handle_norm']+x['name_norm']

            #shingle it

            x['shingles'] = set(
                sh
                for token in x['all_id_norm']
                for sh in utils.getShingles(self.k, token)
            )


        #since we have few samples we can do this super dumbly
    
        for x in tqdm(self.data):
            for y in self.data:
                if x['dumbId'] != y['dumbId']:
                    

                    d = utils.getJaccardDistance(x['shingles'],y['shingles'])
                    if(d < self.maxDistanceRegister):
                        if('neighbors' in x):
                            if not any(n_id == y['dumbId'] for n_id, _ in x['neighbors']):
                                bisect.insort(x['neighbors'],(y['dumbId'],d), key=lambda v: v[1])
                        else:
                            x['neighbors'] = [(y['dumbId'],d)]

                        if('neighbors' in y):
                            if not any(n_id == x['dumbId'] for n_id, _ in y['neighbors']):
                                bisect.insort(y['neighbors'],(x['dumbId'],d), key=lambda v: v[1])
                        else:
                            y['neighbors'] = [(x['dumbId'],d)]

        for x in tqdm(self.data):
            x.pop('shingles')

        self.save_full_data()     

        return self.data

    def checkIfClusterHasNeighbor(self,cluster):
        for id in cluster:
            v = self.distances[id]
            if 'neighbors' not in v:
                return False
        return True

    def getCluster(self, cluster):
        return [self.distances[c] for c in cluster]

    def getClusterCoverageMap(self, cluster):
        c = self.getCluster(cluster)
        coverage = {}
        uniqueness = True
        for n in c:
            year = str(n['_year'])
            month = n.get('_month', '')
            plat = str(n['_platform']).lower()
            tot = year+month+plat
            if tot in coverage:
                uniqueness = False
                coverage[tot] += 1
            else:
                coverage[tot] = 1

        return uniqueness,coverage

    def getClusterIdentity(self, cluster):
        cl = self.getCluster(cluster)
        ids = [(c['handle'], c['name']) for c in cl]
        return ids


    #method by chatgpt
    def getClusterDiameter(self, cluster):
        """
    Compute the diameter of a cluster:
    maximum pairwise Jaccard distance between all members.

    Parameters
    ----------
    cluster : iterable[int]
        Collection of dumbId's

    Returns
    -------
    float
        Max pairwise distance (0 if singleton)
        """
        ids = list(cluster)

        # singleton or empty cluster
        if len(ids) <= 1:
            return 0.0

        # precompute shingles for all members
        shingles_cache = {}
        for idx in ids:
            row = self.distances[idx]

            tokens = normalizeString(row['handle'])+ normalizeString(row['name'])

            shingles = set(
                sh
                for token in tokens
                for sh in utils.getShingles(self.k, token)
            )

            shingles_cache[idx] = shingles

        max_dist = 0.0

        # compute all pairwise distances
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                d = utils.getJaccardDistance(
                    shingles_cache[ids[i]],
                    shingles_cache[ids[j]]
                )
                if d > max_dist:
                    max_dist = d

        return max_dist


    def getAverageDiameter(self, uniqueId, minClusterSize=1):

        counter = 0
        diam = 0
        for clusterId in uniqueId:
            cluster = uniqueId[clusterId]
            if len(cluster) >= minClusterSize:
                counter+=1
                diam += self.getClusterDiameter(cluster)

        return diam/counter if counter > 0 else 0


    #by chatgpt
    def getWorstClusters(self, n, minClusterSize=2, excludeZeroCluster=True):
        buf = []
    
        for cluster_id, cluster in self.uniqueId.items():
            if excludeZeroCluster and cluster_id == 0:
                continue
    
            if len(cluster) < minClusterSize:
                continue
    
            diameter = self.getClusterDiameter(cluster)
            buf.append((cluster_id, diameter, len(cluster), cluster))
    
        buf.sort(key=lambda x: x[1], reverse=True)
    
        return buf[:n]   


    def getNonSingleClusters(self):
        buf = []
        for idx in self.uniqueId:
            if(len(self.uniqueId[idx]) > 1):
                buf.append(self.uniqueId[idx])

        return buf
    
    
    
    def process(self):
        if os.path.exists(self.path):
            self.distances = self.load_full_data()
            if(self.verbose):
                print('Loaded distances')
        else:
            if(self.verbose):
                print('Missing distances, calculating them...')
            self.distances = self.createDistances()

        for x in self.distances:
            x['_year'] = str(x['_year'])
            x['_month'] = str(x.get('_month', ''))

        
        uniqueId = {}
        uniqueId[0] = set()

        processed = set()

        uniqueIdCounter = 1
        a = 0

        trivialFindings = 0

        #we first merge those who have exact same handle
        for x in self.distances:
            if(x['dumbId'] in processed):
                continue

            if(x['handle'] == None):
                uniqueId[uniqueIdCounter] = {x['dumbId'] }
                processed.update({x['dumbId']})
                x['belongsIn'] = uniqueIdCounter
                uniqueIdCounter+=1
                continue

            closeSamePlat = [x]

            
            x['handle'] = str(x['handle']).replace('@', '')

            if('neighbors' in x):
                for closeId ,d in x['neighbors']:
                    if closeId in processed:
                        continue

                    v = self.distances[int(closeId)]
                    if(v['handle'] == None):
                        continue

                    t = str(v['handle'])
                    t = t.replace('@', '')
                    if t == x['handle']:
                        closeSamePlat += [v]

            #we find the uniqueness in files
            original_year = str(x['_year'])
            original_month = x.get('_month','')
            plat = str(x['_platform']).lower()
            tot_orig = original_year+original_month+plat

            combos = {}

            for n in closeSamePlat:
                year = str(n['_year'])
                month = n.get('_month', '')
                plat = str(n['_platform']).lower()
                tot = year+month+plat
                if tot in combos:
                    combos[tot]+=1
                else:
                    combos[tot] = 1
                    

            if all(combos[key] == 1 for key in combos):
                if(len(closeSamePlat) != 1):
                    trivialFindings +=1
                uniqueId[uniqueIdCounter] = {n['dumbId'] for n in closeSamePlat}
                for n in closeSamePlat:
                    n['belongsIn'] = uniqueIdCounter
                processed.update({n['dumbId'] for n in closeSamePlat})
                uniqueIdCounter+=1
            else:
                if(self.verbose):
                    print('This handle is present in too many places : ', x['handle'], ' putting it in 0')
                uniqueId[0].add(x['dumbId'])
                x['belongsIn'] = 0
                processed.update({x['dumbId']})

                if(self.verbose):
                    print('This handle is present in too many places : ', x['handle'], ' putting it in 0')
                ids = {n['dumbId'] for n in closeSamePlat}
                uniqueId[0].update(ids)
                for n in closeSamePlat:
                    n['belongsIn'] = 0
                processed.update(ids)
                a += 1

        if(self.verbose):
            print(a)
        if(self.verbose):
            print('We found', trivialFindings, 'unique peoples accros the dataset!')

        #plot_cluster_size_distribution(self, uniqueId, log_y=False)


        #we now merge the clusters trivially 
        clusteredCount = 0

        idMerged = set()
        for x in uniqueId:
             if x in idMerged:
                continue
             if not self.checkIfClusterHasNeighbor(uniqueId[x]):
                continue

             clusterMembers = self.getCluster(uniqueId[x])
             additions = []
             for v in clusterMembers:
                if 'neighbors' not in v:
                    continue

                neighbors = v['neighbors']
                potentialAdditions = []
                #we iteratively try to add the neighbors to our cluster
                
                errorsHad = 0
                
                for n,d in neighbors:
                    if(d > self.maxDistance):
                        break
                    if n in uniqueId[x]:
                        #skip if already present
                        continue

                    iterationAddition = {'points':{n}, 'd':d}
                    #check if n is in a cluster
                    if 'belongsIn' in self.distances[n]:
                        for c in uniqueId[self.distances[n]['belongsIn']]:
                            #add all of the ppl in the cluster to this one
                            iterationAddition['points'] = iterationAddition['points'].union({c})

                    if(self.assumeSameCategory):
                        if self.distances[n]['category_unified'] != v['category_unified'] and self.distances[n]['category_unified'] != None and v['category_unified'] != None:
                            if(self.punitiveCategoryPolicy):
                                #we found a difference, stop immediately
                                break
                            else:
                                #non punitive, we keep going #TODO we do not increase error but we should maybe
                                continue




                    #check if adding to the group breaks the uniqueness of measures
                    newClusterPoints = uniqueId[x].union(iterationAddition['points'])
                    for add in potentialAdditions:
                        newClusterPoints = newClusterPoints.union(add['points'])

                    uniqueness, _ = self.getClusterCoverageMap(newClusterPoints)
                    if not uniqueness:
                        errorsHad += 1
                        continue

                    if errorsHad >= self.maxClosenessError:
                        break

                    potentialAdditions.append(iterationAddition)
                    #we merge the cluster ! 

                additions.append(potentialAdditions)

             
             
            #for each cluster addition, we rank then based on how many times they appeared in the search, and what is the mean distance they were found
             counts = {}
             for addition in additions:
                for add in addition:
                    d = add['d']
                    cluster =  frozenset(add['points'])
                    if cluster in counts:
                        counts[cluster] = (counts[cluster][0]+d,counts[cluster][1]+1)
                    else:
                        counts[cluster] = (d, 1)
                    
             #keep only the ones that are added enough of times
             counts = {
                c: (total_d / cnt, cnt / len(uniqueId[x]))
                for c, (total_d, cnt) in counts.items()
                if (cnt / len(uniqueId[x])) >= self.minRepetitionRate
            }


             #we then sort from the smallest distance to the max (to get the order of addition)
             additions = [(c,counts[c]) for c in counts]
             additionsSorted = sorted(additions, key=lambda x: x[1][0])

             #addition loop      
             for addition in additionsSorted:
                   new_points = set(addition[0])
                
                   newClusterPoints = uniqueId[x].union(new_points)
                   uniqueness, _ = self.getClusterCoverageMap(newClusterPoints)
                   if not uniqueness:
                       continue
                
                   # find all old cluster ids before reassigning
                   old_cluster_ids = set()
                   for p in new_points:
                       if 'belongsIn' in self.distances[p]:
                           old_cluster_ids.add(self.distances[p]['belongsIn'])
                
                   # move points
                   uniqueId[x].update(new_points)
                
                   # keep belongsIn consistent
                   for p in new_points:
                       self.distances[p]['belongsIn'] = x
                
                   # mark merged clusters for deletion, except the target one
                   for old_cid in old_cluster_ids:
                       if old_cid != x:
                           idMerged.add(old_cid)
                
                   clusteredCount += 1
                

                
        #remove old clusters
        for idx in idMerged:
            del uniqueId[idx]

        if(self.verbose):
            print(clusteredCount)

        if(self.verbose):
            print("Diameter of clusters >= 2 : " + str(self.getAverageDiameter(uniqueId,2)))

        if(self.verbose):
            print(ids)
        #plot_cluster_size_distribution(self, uniqueId, log_y=False)

        self.uniqueId = uniqueId

        #now we backtrack

        splitCounter = 0
        for idx in list(self.uniqueId):
            split, splits = self.shouldSplitCluster(self.uniqueId[idx], ratioThreshold=self.backTrackSplitThreshold)

            if(split):
                if len(splits[0].intersection(splits[1])) > 0:
                    if(self.verbose):
                        print("overlap detected")
                    if(self.verbose):
                        print(splits[0].intersection(splits[1]))
                    raise ValueError('Overlap')
                splitCounter += 1
                self.uniqueId[uniqueIdCounter] = splits[1]
                self.uniqueId[idx] = splits[0]
                uniqueIdCounter += 1
                #we split

        if(self.verbose):
            print("We splitted :", splitCounter, "clusters.")


    #by chatGPT, computes a in cluster hierarchical clustering to allow to backtrack in case of wrong descicions
    def shouldSplitCluster(self, cluster, ratioThreshold=2, minSize=3, minChildSize=2):
        pts = list(cluster)
    
        if len(pts) < minSize:
            return False, [set(cluster)]
    
        #compute pairwise distance matrix
        shingles = {}
        for p in pts:
            row = self.distances[p]
            tokens = normalizeString(row['handle']) + normalizeString(row['name'])
            shingles[p] = set(
                sh
                for token in tokens
                for sh in utils.getShingles(self.k, token)
            )
    
        dists = {}
        clusters = [{p} for p in pts]
    
        for i in range(len(pts)):
            for j in range(i+1, len(pts)):
                d = utils.getJaccardDistance(shingles[pts[i]], shingles[pts[j]])
                dists[(pts[i], pts[j])] = d
                dists[(pts[j], pts[i])] = d
    
        #average linkage until 2 clusters remain
        while len(clusters) > 2:
            best = None
            bestDist = float('inf')
    
            for i in range(len(clusters)):
                for j in range(i+1, len(clusters)):
                    a = clusters[i]
                    b = clusters[j]
    
                    vals = []
                    for x in a:
                        for y in b:
                            vals.append(dists[(x,y)])
    
                    meanD = sum(vals)/len(vals)
    
                    if meanD < bestDist:
                        bestDist = meanD
                        best = (i,j)
    
            i,j = best
            clusters[i] = clusters[i].union(clusters[j])
            del clusters[j]
    
        c1 = clusters[0]
        c2 = clusters[1]
    
        if len(c1) < minChildSize or len(c2) < minChildSize:
            return False, [set(cluster)]
    
        def meanIntra(c):
            vals = []
            c = list(c)
            for i in range(len(c)):
                for j in range(i+1, len(c)):
                    vals.append(dists[(c[i], c[j])])
            return sum(vals)/len(vals) if len(vals) > 0 else 0
    
        def meanCross(c1, c2):
            vals = []
            for x in c1:
                for y in c2:
                    vals.append(dists[(x,y)])
            return sum(vals)/len(vals) if len(vals) > 0 else 0
    
        intra1 = meanIntra(c1)
        intra2 = meanIntra(c2)
        intra = (intra1 + intra2) / 2
        cross = meanCross(c1, c2)
    
        if intra == 0:
            score = float('inf') if cross > 0 else 1
        else:
            score = cross / intra
    
        if score >= ratioThreshold:
            return True, [c1, c2]
    
        return False, [set(cluster)]

    #by chat
    def getMeanClosestClusterDistanceFromGraph(self, uniqueId, k=5, minClusterSize=1):
        belongs = {}
        for cid in uniqueId:
            if cid == 0:
                continue
            for x in uniqueId[cid]:
                belongs[x] = cid
    
        vals = []
    
        for cid in uniqueId:
            if cid == 0:
                continue
            if len(uniqueId[cid]) < minClusterSize:
                continue
    
            bests = {}
    
            for x in uniqueId[cid]:
                v = self.distances[x]
    
                if 'neighbors' not in v:
                    continue
    
                pointBest = {}
    
                for n, d in v['neighbors']:
                    if n not in belongs:
                        continue
    
                    otherCid = belongs[n]
    
                    if otherCid == cid:
                        continue
    
                    if otherCid not in pointBest or d < pointBest[otherCid]:
                        pointBest[otherCid] = d
    
                for otherCid in pointBest:
                    if otherCid in bests:
                        bests[otherCid].append(pointBest[otherCid])
                    else:
                        bests[otherCid] = [pointBest[otherCid]]
    
            if len(bests) == 0:
                continue
    
            neighDists = [sum(bests[c]) / len(bests[c]) for c in bests]
            neighDists.sort()
    
            vals.append(sum(neighDists[:k]) / min(k, len(neighDists)))
    
        return sum(vals) / len(vals) if len(vals) > 0 else 0


def plot_cluster_platform_distribution(self, uniqueId, exclude_zero_cluster=True, log_y=True):
    """
    Plot cluster size distribution, split by number of platforms per cluster.

    Colors:
        red   = 1 platform
        blue  = 2 platforms
        green = 3 platforms
    """

    import numpy as np
    import matplotlib.pyplot as plt

    size_1 = []
    size_2 = []
    size_3 = []

    for cluster_id, members in uniqueId.items():
        if exclude_zero_cluster and cluster_id == 0:
            continue
        if not members:
            continue

        cluster = self.getCluster(members)

        platforms = set(str(c['_platform']).lower() for c in cluster)
        nb_platforms = len(platforms)

        size = len(members)

        if nb_platforms == 1:
            size_1.append(size)
        elif nb_platforms == 2:
            size_2.append(size)
        else:
            size_3.append(size)

    all_sizes = size_1 + size_2 + size_3

    if not all_sizes:
        print("No clusters to plot.")
        return

    max_size = max(all_sizes)
    bins = np.arange(1, max_size + 2) - 0.5

    plt.figure(figsize=(10, 6))

    plt.hist(
        [size_1, size_2, size_3],
        bins=bins,
        stacked=True,
        color=["red", "blue", "green"],
        label=["1 platform", "2 platforms", "3 platforms"],
        edgecolor="black"
    )

    plt.xticks(range(1, max_size + 1))
    plt.xlabel("Cluster size")
    plt.ylabel("Number of clusters")
    plt.title("Cluster Size Distribution by Platform Coverage")

    if log_y:
        plt.yscale("log")

    plt.legend()

    plt.tight_layout()
    plt.show()
