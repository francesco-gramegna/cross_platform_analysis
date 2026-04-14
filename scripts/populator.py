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
    def __init__(self, data, k=3, maxDistanceRegister = 0.8 , maxDistance=0.8, maxClosenessError=2, minRepetitionRate=0):
        self.data = data
        self.k = k
        self.path = 'temp/distances.csv'
        self.maxDistanceRegister = maxDistanceRegister
        self.maxDistance = maxDistance
        self.maxClosenessError = maxClosenessError
        self.minRepetitionRate = minRepetitionRate

    
    def save_full_data(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

        print(f"Full dataset saved to {self.path}")

    def load_full_data(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def createDistances(self):
        
        counter = 0
        for x in self.data:
            x['dumbId'] = counter
            counter += 1

            x['handle_norm'] = normalizeString(str(x['handle']))
            x['name_norm'] = normalizeString(str(x['name']))
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

        
    
    def process(self):
        if os.path.exists(self.path):
            self.distances = self.load_full_data()
            print('Loaded distances')
        else:
            print('Missing distances, calculating them...')
            self.distances = self.createDistances()

        
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
                print('This handle is present in too many places : ', x['handle'], ' putting it in 0')
                uniqueId[0].add(x['dumbId'])
                x['belongsIn'] = 0
                processed.update({x['dumbId']})

                print('This handle is present in too many places : ', x['handle'], ' putting it in 0')
                ids = {n['dumbId'] for n in closeSamePlat}
                uniqueId[0].update(ids)
                for n in closeSamePlat:
                    n['belongsIn'] = 0
                processed.update(ids)
                a += 1

        print(a)
        print('We found', trivialFindings, 'unique peoples accros the dataset!')

        plot_cluster_size_distribution(self, uniqueId, log_y=False)


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
                newClusterPoints = uniqueId[x].union(addition[0])
                uniqueness, _ = self.getClusterCoverageMap(newClusterPoints)

                if not uniqueness:
                    #todo should we break?
                    continue
                
                uniqueId[x].update(addition[0])
                #remove the old Id
                
                idOfOldCluster = self.distances[list(addition[0])[0]]['belongsIn']
                idMerged.add(idOfOldCluster)

                clusteredCount += 1



        print(clusteredCount)
        plot_cluster_size_distribution(self, uniqueId, log_y=False)


        


        
