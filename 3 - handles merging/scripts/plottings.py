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


def plot_unique_id_size_distribution(self, uniqueId):
    from collections import defaultdict
    import matplotlib.pyplot as plt

    id_to_platform = {
        x["dumbId"]: x["_platform"]
        for x in self.distances
    }

    size_platform_counts = defaultdict(lambda: defaultdict(int))

    for id_set in uniqueId.values():
        if not id_set:
            continue

        size = len(id_set)
        any_id = next(iter(id_set))
        platform = id_to_platform.get(any_id, "unknown")

        size_platform_counts[size][platform] += 1

    if not size_platform_counts:
        print("No data to plot.")
        return

    sizes = sorted(size_platform_counts.keys())
    platforms = sorted({
        p for counts in size_platform_counts.values() for p in counts
    })

    platform_values = {p: [] for p in platforms}

    for size in sizes:
        for p in platforms:
            count = size_platform_counts[size].get(p, 0)
            platform_values[p].append(count)

    bottom = [0] * len(sizes)

    for p in platforms:
        vals = platform_values[p]
        plt.bar(sizes, vals, bottom=bottom, label=p)
        bottom = [b + v for b, v in zip(bottom, vals)]

    plt.xlabel("Set size")
    plt.ylabel("Count (log scale)")
    plt.title("Count of trivial clusters by size and platform (log scale)")

    plt.yscale("log")  

    plt.legend()
    plt.show()


def plot_cluster_size_distribution(self, uniqueId, exclude_zero_cluster=True, log_y=True):
    """
    Panel 1:
    Plot the distribution of cluster sizes.

    Parameters
    ----------
    uniqueId : dict[int, set[int]]
        Mapping from cluster id to member row ids.
    exclude_zero_cluster : bool
        If True, excludes cluster 0 from the plot.
    log_y : bool
        If True, use log scale on y-axis for readability.
    """
    cluster_sizes = []

    for cluster_id, members in uniqueId.items():
        if exclude_zero_cluster and cluster_id == 0:
            continue
        if not members:
            continue
        cluster_sizes.append(len(members))

    if not cluster_sizes:
        print("No clusters to plot.")
        return

    max_size = max(cluster_sizes)
    bins = np.arange(1, max_size + 2) - 0.5

    plt.figure(figsize=(10, 6))
    plt.hist(cluster_sizes, bins=bins, edgecolor='black')
    plt.xticks(range(1, max_size + 1))
    plt.xlabel("Cluster size")
    plt.ylabel("Number of clusters")
    plt.title("Cluster Size Distribution")

    if log_y:
        plt.yscale("log")

    plt.tight_layout()
    plt.show()

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
