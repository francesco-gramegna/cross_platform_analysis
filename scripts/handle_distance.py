import re
import numpy as np
import matplotlib.pyplot as plt
import utils
from plottings import plotLenHist


def normalizeString_old(s, sev):
    if(s == None):
        return []

    toRemove = ["official","tiktok","instagram","youtube", "entertainment"]
    s = s.lower()
    s = re.sub(r'[^a-z0-9 ]', '', s.strip())
    for x in toRemove:
        s = s.replace(x, '')
    s = s.split(' ') 
    return s

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


data = utils.load_csvs_to_dicts("cleaned_dataset/updated/*")
print(data)

#Normalisation of handles and name
handles = [dict(r) for r in data]

for x in handles:
    x['handle_norm'] = normalizeString(x['handle'])
    x['name_norm'] = normalizeString(x['name'])
    x['all_id_norm'] =  x['handle_norm']+x['name_norm']

    #shingle it
    x['shingles'] = [sh for sh in [utils.getShingles(3,u) for u in x['all_id_norm']]]


#we try to get from intagram to youtube

#since we have few samples we can do this dumbly:


counter = 0
for x in handles:
    if 'youtube_nov' in x['source_file']:
        distances = []
        for y in handles:
            if 'instagram_nov' in y['source_file']:
                d = utils.getJaccardDistance(x['all_id_norm'],y['all_id_norm'])
                distances.append(d)
                if(d < 0.7 and d > 0):
                    counter+=1
                    print(x['handle'],'     ', x['name'], ' ->  ', y['handle'], '   ', y['name'], '  ', d , ' ')
                     
        x['distances'] = distances
        #plt.plot(distances)
        #plt.show()




print(counter)
#plotLenHist(handles, 'shingles')




#normalisation of the name


