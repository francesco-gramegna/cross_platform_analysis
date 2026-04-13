import csv
import glob
import os
from typing import List, Dict, Any

def getShingles(k, s):
    #perform the trick we discussed to avoid to deal with edge cases
    while(len(s) < k):
        s += ' '

    shingles = {s[i:i+k] for i in range(len(s) - k + 1)}
    return shingles


def getJaccardDistance(a,b):
    a = set(a)
    b = set(b)
    if(len(a) == 0 and len(b) == 0):
        return 0

    jaccard = len(a & b) / len(a | b) 
 
    return 1 - jaccard
    


def normalize_key(key: str) -> str:
    """
    Normalize keys like 'handle_youtube' -> 'handle'
    """
    key = key.replace(' ', '')
    if "_" in key:
        base = key.split("_")[0]
        if base in {"handle", "name"}:
            return base
    return key


def load_csvs_to_dicts(file_pattern: str) -> List[Dict[str, Any]]:
    all_data = []
    missing_values = {"", "N/A", "NA", "null", "None"}
    
    files = glob.glob(file_pattern)
    
    for file in files:
        file_name = os.path.basename(file)
        
        with open(file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                cleaned_row = {}
                
                for key, value in row.items():
                    new_key = normalize_key(key)
                    
                    if value is None:
                        cleaned_value = None
                    else:
                        value = value.strip()
                        cleaned_value = None if value in missing_values else value
                    
                    # If multiple columns map to same key, prefer non-null
                    if new_key in cleaned_row:
                        if cleaned_row[new_key] is None and cleaned_value is not None:
                            cleaned_row[new_key] = cleaned_value
                    else:
                        cleaned_row[new_key] = cleaned_value
                
                cleaned_row["source_file"] = file_name
                all_data.append(cleaned_row)
    
    return all_data
