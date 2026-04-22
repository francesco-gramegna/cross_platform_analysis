import plottings
import random
from populator import NamePopulator
import utils


def fmt_record(r):
    handle = r.get("handle")
    name = r.get("name")
    cat = r.get("category_unified")
    year = r.get("_year")
    month = r.get("_month", "")
    platform = r.get("_platform")
    dumb_id = r.get("dumbId")
    return (
        f"dumbId={dumb_id} | "
        f"handle={repr(handle)} | "
        f"name={repr(name)} | "
        f"category={repr(cat)} | "
        f"year={repr(year)} | "
        f"month={repr(month)} | "
        f"platform={repr(platform)}"
    )


def print_singleton_with_neighbors(pop, cluster_id, max_neighbors=5):
    cluster = pop.uniqueId[cluster_id]
    if len(cluster) != 1:
        return

    point_id = next(iter(cluster))
    row = pop.distances[point_id]

    print("=" * 120)
    print(f"SINGLETON CLUSTER {cluster_id}")
    print("POINT:")
    print("  " + fmt_record(row))

    neighbors = row.get("neighbors", [])
    if not neighbors:
        print("  No neighbors found.")
        return

    print(f"\nCLOSEST {min(max_neighbors, len(neighbors))} NEIGHBORS:")
    for neighbor_id, dist in neighbors[:max_neighbors]:
        neigh = pop.distances[neighbor_id]
        print(f"  distance={dist:.4f}")
        print("   -> " + fmt_record(neigh))


def print_cluster(pop, cluster_id):
    cluster = pop.uniqueId[cluster_id]
    print("=" * 120)
    print(f"NON-SINGLETON CLUSTER {cluster_id} | size={len(cluster)}")

    members = [pop.distances[idx] for idx in cluster]
    members = sorted(
        members,
        key=lambda r: (
            str(r.get("handle")),
            str(r.get("name")),
            str(r.get("_year")),
            str(r.get("_month", "")),
            str(r.get("_platform")),
        ),
    )

    for m in members:
        print("  " + fmt_record(m))


def sample_singletons_with_neighbors(pop, target_n=20):
    eligible = []
    for cid, cluster in pop.uniqueId.items():
        if cid == 0 or len(cluster) != 1:
            continue

        point_id = next(iter(cluster))
        row = pop.distances[point_id]
        if len(row.get("neighbors", [])) > 0:
            eligible.append(cid)

    n = min(target_n, len(eligible))
    return random.sample(eligible, n)


def main():
    random.seed(42)

    data = utils.load_csvs_to_dicts("cleaned_dataset/updated/*")

    pop = NamePopulator(
        data,
        k=3,
        maxDistanceRegister=0.8,
        maxDistance=0.55,              # set your chosen threshold here
        maxClosenessError=1,
        minRepetitionRate=0.5,
        assumeSameCategory=True,
        punitiveCategoryPolicy=True,
        backTrackSplitThreshold=2,
        verbose=True,
    )

    pop.process()

    singleton_cluster_ids = [
        cid for cid, cluster in pop.uniqueId.items()
        if cid != 0 and len(cluster) == 1
    ]

    nonsingleton_cluster_ids = [
        cid for cid, cluster in pop.uniqueId.items()
        if cid != 0 and len(cluster) > 1
    ]

    sampled_singletons = sample_singletons_with_neighbors(pop, target_n=20)
    sampled_multi = random.sample(
        nonsingleton_cluster_ids,
        min(20, len(nonsingleton_cluster_ids))
    )

    print("\n" + "#" * 120)
    print(f"Total clusters: {len(pop.uniqueId)}")
    print(f"Singleton clusters: {len(singleton_cluster_ids)}")
    print(f"Singleton clusters with at least 1 neighbor: {len(sampled_singletons)} sampled")
    print(f"Non-singleton clusters: {len(nonsingleton_cluster_ids)}")
    print("#" * 120 + "\n")

    print("\n" + "#" * 120)
    print(f"RANDOM SAMPLE OF {len(sampled_singletons)} SINGLETON CLUSTERS WITH NEIGHBORS")
    print("#" * 120 + "\n")

    for cid in sampled_singletons:
        print_singleton_with_neighbors(pop, cid, max_neighbors=5)

    print("\n" + "#" * 120)
    print(f"RANDOM SAMPLE OF {min(20, len(nonsingleton_cluster_ids))} NON-SINGLETON CLUSTERS")
    print("#" * 120 + "\n")

    for cid in sampled_multi:
        print_cluster(pop, cid)

    plottings.plot_cluster_platform_distribution(pop,pop.uniqueId)

    print(len(pop.uniqueId))
    print(len(pop.data))


if __name__ == "__main__":
    main()
