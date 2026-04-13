import re
import numpy as np
import matplotlib.pyplot as plt
import utils

def plotLenHist(handles, key):
    # all individual lengths
    handles_len = [len(s) for x in handles for s in x[key] if s]

    print(np.mean(handles_len))
    print(np.std(handles_len))

    inst_len = [
        len(s)
        for x in handles
        if x['source_file'].split('_')[0] == 'instagram'
        for s in x[key]
        if s
    ]
    youtube_len = [
        len(s)
        for x in handles
        if x['source_file'].split('_')[0] == 'youtube'
        for s in x[key]
        if s
    ]
    tiktok_len = [
        len(s)
        for x in handles
        if x['source_file'].split('_')[0] == 'tiktok'
        for s in x[key]
        if s
    ]

    plt.hist(
        [inst_len, tiktok_len, youtube_len],
        bins=25,
        stacked=True,
        label=['instagram', 'tiktok', 'youtube'],
        alpha=0.8
    )
    plt.xlabel("String length")
    plt.ylabel("Count")

    mu = np.mean(handles_len)
    sigma = np.std(handles_len)

    plt.axvline(mu, color='red', label='Mean length')
    plt.axvline(mu + sigma, color='blue', label='Standard deviation')
    plt.axvline(mu - sigma, color='blue')

    plt.title("Histogram of string lengths by platform")
    plt.legend()
    plt.show()   
