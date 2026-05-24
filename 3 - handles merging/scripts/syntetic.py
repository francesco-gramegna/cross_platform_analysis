import random
import itertools
from collections import defaultdict
from populator import NamePopulator


def reviewPipelineCode(seed=42):
    random.seed(seed)

    # -------------------------
    # synthetic influencer base
    # -------------------------
    base = [
        ("Luna Rivera", "beauty"),
        ("Mia Thompson", "beauty"),
        ("Sofia Bennett", "fashion"),
        ("Chloe Martin", "fashion"),
        ("Emma Clarke", "fitness"),
        ("Ava Brooks", "fitness"),
        ("Isabella Reed", "music"),
        ("Camila Hayes", "music"),
        ("Olivia Parker", "lifestyle"),
        ("Harper Diaz", "lifestyle"),
        ("Noah Carter", "gaming"),
        ("Liam Foster", "gaming"),
        ("Ethan Hughes", "tech"),
        ("Mason Bell", "tech"),
        ("Lucas Perry", "food"),
        ("Benjamin Ross", "food"),
        ("Aria Collins", "travel"),
        ("Ella Ward", "travel"),
        ("Grace Morales", "parenting"),
        ("Zoe Simmons", "parenting"),
    ]

    years = ["2022", "2023", "2024"]
    platforms = ["instagram", "tiktok", "youtube"]

    def clean_handle(name):
        return (
            name.lower()
            .replace(" ", "")
            .replace("'", "")
            .replace("-", "")
        )

    def typo_name(name):
        if name is None:
            return None

        ops = []

    # deletion
        if len(name) > 4:
            i = random.randint(0, len(name)-1)
            ops.append(name[:i] + name[i+1:])

    # swap
        if len(name) > 3:
            i = random.randint(0, len(name)-2)
            ops.append(name[:i] + name[i+1] + name[i] + name[i+2:])

    # duplicate char
        i = random.randint(0, len(name)-1)
        ops.append(name[:i] + name[i]*2 + name[i+1:])

    # replace with similar char
        replacements = {'o':'0','i':'l','l':'i','e':'3','a':'@','s':'5'}
        new = list(name)
        for i,c in enumerate(new):
            if c.lower() in replacements and random.random() < 0.3:
                new[i] = replacements[c.lower()]
        ops.append(''.join(new))

    # remove space
        ops.append(name.replace(" ", ""))

    # random casing
        ops.append(name.upper())
        ops.append(name.lower())

        return random.choice(ops)


    def noisy_handle(base_handle):
        if random.random() < 0.2:
            return None  # 🔥 more missing handles
    
        h = base_handle
    
        # random corruption
        if random.random() < 0.3:
            i = random.randint(0, len(h)-1)
            h = h[:i] + random.choice("abcdefghijklmnopqrstuvwxyz") + h[i+1:]
    
        # add noise tokens
        suffixes = ["official", "real", "tv", "yt", "xx", "01", "_", "__"]
        prefixes = ["@", "", "_", "."]
    
        h = random.choice(prefixes) + h
    
        if random.random() < 0.4:
            h += random.choice(suffixes)
    
        # insert separators randomly
        if random.random() < 0.3:
            i = random.randint(1, len(h)-1)
            h = h[:i] + random.choice([".", "_"]) + h[i:]
    
        return h


    def noisy_name(full_name, handle_base):
        if random.random() < 0.1:
            return None  # 🔥 more missing names
    
        first = full_name.split()[0]
        last = full_name.split()[-1]
    
        opts = [
            full_name,
            typo_name(full_name),
            typo_name(first),
            typo_name(last),
            first,
            last,
            first + " " + last[0],
            handle_base,
            full_name + " Official",
            full_name + " ✔",
            full_name + " 🔥",
        ]
    
        return random.choice(opts)


    def maybe_wrong_alias(full_name):
        # small amount of confusing display-name noise
        aliases = {
            "Luna Rivera": "Luna R.",
            "Mia Thompson": "Mia T",
            "Sofia Bennett": "Sofi",
            "Chloe Martin": "Chlo",
            "Emma Clarke": "Em",
            "Ava Brooks": "Ava B",
            "Isabella Reed": "Isa",
            "Camila Hayes": "Cami",
            "Olivia Parker": "Liv",
            "Harper Diaz": "Harper D",
            "Noah Carter": "Noah C",
            "Liam Foster": "Liam F",
            "Ethan Hughes": "Ethan H",
            "Mason Bell": "Mase",
            "Lucas Perry": "Luke Perry",
            "Benjamin Ross": "Ben Ross",
            "Aria Collins": "Aria C",
            "Ella Ward": "Ella W",
            "Grace Morales": "Gracie",
            "Zoe Simmons": "Zoe S",
        }
        if random.random() < 0.18:
            return aliases.get(full_name, full_name)
        return full_name

    # ------------------------------------------------
    # generate dataset: 20 unique influencers, 2022-24
    # ------------------------------------------------
    data = []
    true_people = {}

    for pid, (full_name, category) in enumerate(base):
        true_people[pid] = full_name
        handle_base = clean_handle(full_name)

        n_records = random.randint(6, 10)

        used_slots = set()
        for _ in range(n_records):
            year = random.choice(years)
            platform = random.choice(platforms)

            # keep uniqueness mostly realistic at record level
            tries = 0
            while (year, platform) in used_slots and tries < 10:
                year = random.choice(years)
                platform = random.choice(platforms)
                tries += 1
            used_slots.add((year, platform))

            handle = noisy_handle(handle_base)
            name = noisy_name(maybe_wrong_alias(full_name), handle_base)

            row = {
                "handle": handle,
                "name": name,
                "_year": str(year),
                "_month": str(random.randint(1, 12)),
                "_platform": platform,
                "category_unified": category,
                "true_person_id": pid,
            }

            data.append(row)

    # ------------------------------------------------------
    # add a few "hard negatives" that should NOT be merged
    # ------------------------------------------------------
    # Similar-looking people across same category
    hard_negatives = [
    {
        "handle": "lunariveraofficial",
        "name": "Luna Riviera",
        "_year": "2023",
        "_month": "5",
        "_platform": "instagram",
        "category_unified": "beauty",
        "true_person_id": 1000,
    },
    {
        "handle": "liamfosterr",
        "name": "Liam Foster",
        "_year": "2024",
        "_month": "4",
        "_platform": "youtube",
        "category_unified": "gaming",
        "true_person_id": 1001,
    },
    {
        "handle": "ethanhughesofficial",
        "name": "Ethan Huges",
        "_year": "2022",
        "_month": "8",
        "_platform": "tiktok",
        "category_unified": "tech",
        "true_person_id": 1002,
    },
    {
        "handle": "zoesimmonss",
        "name": "Zoe Simmons Official",
        "_year": "2024",
        "_month": "10",
        "_platform": "instagram",
        "category_unified": "parenting",
        "true_person_id": 1003,
    },
]

    data.extend(hard_negatives)

    # ------------------------------------------------
    # run your pipeline
    # ------------------------------------------------
    pop = NamePopulator(
        data,
        k=3,
        maxDistanceRegister=0.8,
        maxDistance=0.6,
        maxClosenessError=2,
        minRepetitionRate=1,
        assumeSameCategory=True,
        punitiveCategoryPolicy=True,
        backTrackSplitThreshold=2,
        verbose=False,
    )

    pop.process()

    # ------------------------------------------------
    # evaluate pairwise FPR / FNR
    # ------------------------------------------------
    # predicted cluster map
    pred_cluster_of = {}
    for cid in pop.uniqueId:
        for idx in pop.uniqueId[cid]:
            pred_cluster_of[idx] = cid

    tp = 0
    tn = 0
    fp = 0
    fn = 0

    # all record pairs
    for i, j in itertools.combinations(range(len(data)), 2):
        same_true = data[i]["true_person_id"] == data[j]["true_person_id"]
        same_pred = pred_cluster_of.get(i) == pred_cluster_of.get(j)

        if same_true and same_pred:
            tp += 1
        elif same_true and not same_pred:
            fn += 1
        elif not same_true and same_pred:
            fp += 1
        else:
            tn += 1

    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0

    # ------------------------------------------------
    # compact summary
    # ------------------------------------------------
    true_counts = defaultdict(int)
    for row in data:
        true_counts[row["true_person_id"]] += 1

    print("========== REVIEW PIPELINE ==========")
    print("rows :", len(data))
    print("true influencers :", len(set(r["true_person_id"] for r in data)))
    print("predicted clusters :", len(pop.uniqueId))
    print("")
    print("TP :", tp)
    print("FP :", fp)
    print("TN :", tn)
    print("FN :", fn)
    print("")
    print("FPR :", round(fpr, 4))
    print("FNR :", round(fnr, 4))
    print("Precision :", round(precision, 4))
    print("Recall :", round(recall, 4))


    print("\n========== SAMPLE BY TRUE PERSON ==========\n")

    shown = set()
    for r in data:
        pid = r["true_person_id"]
        if pid in shown:
            continue

        print("TRUE PERSON:", pid)
        rows = [x for x in data if x["true_person_id"] == pid][:5]

        for rr in rows:
            print("   ", rr["handle"], "|", rr["name"])

        print("")
        shown.add(pid)

        if len(shown) >= 5:
            break

    return {
        "data": data,
        "pop": pop,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "fpr": fpr,
        "fnr": fnr,
        "precision": precision,
        "recall": recall,
    }

reviewPipelineCode()
