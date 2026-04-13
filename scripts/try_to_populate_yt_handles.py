import utils

data = utils.load_csvs_to_dicts("../crude_dataset/kaggle_2022/*")

data = [x for x in data if 'youtube' in x['source_file']]

count = {}

for x in data:
    han = x['handle'] 
    if han in count:
        count[han] += 1
    else:
        count[han] = 1


total = {1:0, 2:0, 3:0, 4:0, 5:0}

for x in count.keys():
    if(count[x] > 5):
        print(x)
    total[count[x]] += 1


print(total)

#We might have duplicate entries ???
    
    



