"""
2024 数据清洗：三平台统一关键词规则 + 优先级映射 → 7 类
优先级基于共现分析结果（低共现 = 高专一 = 优先级高）
"""
import pandas as pd
import re
from pathlib import Path

ROOT    = Path("/Users/pzy/Documents/DS Practice/data_raw/2024_output")   # 改成你实际的根
OUT_DIR = ROOT 


# ========== 1. 映射规则（按优先级从高到低排）==========
# 原则：
#   - 专一性高的类放前面（Sports/Beauty&Fashion 词专一度高）
#   - 大杂烩类放后面（Entertainment/Lifestyle 词共现度高，兜底）
#   - 三个平台共用这套规则（保 RQ2a 可比）
CATEGORY_RULES_2024 = [
    # Tier 1: 共现 < 2.0，一触即中
    ("Sports", [
        "sports", "sport", "soccer", "football", "basketball",
        "tennis", "racing", "fitness", "gym", "athlete", "yoga",
        "outdoor activity", "adventure"
    ]),

    # Tier 2: 专一性不错，放前面避免被 Entertainment 抢走
    ("Beauty&Fashion", [
        "beauty", "fashion", "modeling", "makeup", "cosmetics",
        "skincare", "self care", "hair", "accessories",
        "clothing", "luxury", "wedding"
    ]),

    # Tier 3: 知识信息类，词专一度中等但语义清晰
    ("Knowledge&Info", [
        "news", "politics", "journalists", "journalism",
        "education", "upskilling",
        "business", "finance", "economics",
        "marketing", "advertising", "career",
        "literature", "book", "health", "medical",
        "society","literature", "book", "books", "author", "authors"
    ]),

    # Tier 4: 科技游戏类，样本少但词专一
    ("Tech&Gaming", [
        "gaming", "video game", "video games", "video gaming",
        "games", "esports", "cosplay",
        "tech", "technology", "science", "engineering",
        "computer", "gadget", "virtualization", "automotive",
        "auto", "vehicles", "cars"
    ]),

    # Tier 5: Music（词频高但共现中等，放中位）
    ("Music", [
        "music", "singer", "musician", "rapper", "songwriting",
        "band", "producers", "dance", "dancing", "dj",
        "glazba", "musik", "sica"   # 多语言：克罗地亚/德/葡
    ]),

    # Tier 6: Entertainment（高频但共现高，放后面兜底）
    ("Entertainment", [
        "actor", "actors", "acting", "drama", "cinema",
        "movie", "film", "shows", "show", "television",
        "celebrity", "celebrities", "celebrities",
        "humor", "humour", "funny", "comedy", "memes",
        "animation", "entertainment", "entretenimento",
        "host", "events"
    ]),

    # Tier 7: Lifestyle（最宽，所有没落到前面的生活类都归这）
    ("Lifestyle", [
        "lifestyle", "life", "family", "parenting", "moms",
        "food", "cooking", "chef", "drink",
        "travel", "animals", "pets",
        "photography", "nature",
        "art", "arts", "artist", "crafts", "diy",
        "home", "garden", "interior",
        "romance", "religion","food", "foods", "animal", "animals", "pet", "pets"
    ]),
]


# ========== 2. 映射函数 ==========
def map_topic_to_category(raw_text):
    """
    把 2024 TOPIC OF INFLUENCE 字段映射到 7 类。
    按 CATEGORY_RULES_2024 的顺序遍历，第一个匹配到关键词的类即为归属。
    
    NA    → 原始缺失
    Other → 有文本但无关键词匹配
    """
    if pd.isna(raw_text):
        return "NA"
    
    # 预处理：驼峰切分 + 分隔符归一化
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(raw_text))
    text = re.sub(r"[,/&;|]+", " ", text).lower()
    
    for category, keywords in CATEGORY_RULES_2024:
        for kw in keywords:
            # 词边界匹配，避免 "art" 匹配到 "party"
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, text):
                return category
    return "Other"


# ========== 3. 主流程：三个平台分别跑 ==========
all_data = []
quality_report = []

for platform in ["Instagram", "YouTube", "TikTok"]:
    f = OUT_DIR / f"concat_2024_{platform}.csv"
    if not f.exists():
        print(f"⚠️  {platform} 文件不存在，跳过")
        continue
    
    df = pd.read_csv(f)
    n_total = len(df)
    
    # 去重（按 NAME，NAME 里含 @handle 是唯一标识）
    df = df.sort_values("_is_global", ascending=False)
    df = df.drop_duplicates(subset=["NAME"], keep="first")
    n_dedup = len(df)
    
    # 做映射
    
    df["category_unified"]  = df["TOPIC OF INFLUENCE"].apply(map_topic_to_category)
    df["_year"]             = 2024
    
    # 统计
    n_na      = (df["category_unified"] == "NA").sum()
    n_other   = (df["category_unified"] == "Other").sum()
    n_mapped  = n_dedup - n_na - n_other
    
    quality_report.append({
        "platform":        platform,
        "n_raw":           n_total,
        "n_dedup":         n_dedup,
        "n_na":            n_na,
        "n_other":         n_other,
        "n_mapped":        n_mapped,
        "na_rate":         round(n_na / n_dedup, 3),
        "other_rate":      round(n_other / n_dedup, 3),
        "effective_rate":  round(n_mapped / n_dedup, 3),
    })
    
    all_data.append(df)


# ========== 4. 输出报告 ==========
report_df = pd.DataFrame(quality_report)
print("========== 2024 映射质量报告 ==========")
print(report_df.to_string(index=False))
report_df.to_csv(OUT_DIR / "merge_2024_report.csv", index=False)


# ========== 5. 分布检查 ==========
big = pd.concat(all_data, ignore_index=True, sort=False)
big.to_csv(OUT_DIR / "merged_2024_all.csv", index=False, encoding="utf-8-sig")
print(f"\n合并后总行数: {len(big)}, 保存至 merged_2024_all.csv")

print("\n========== 7 类分布（按平台）==========")
dist = big.groupby(["_platform", "category_unified"]).size().unstack(fill_value=0)
print(dist)

print("\n========== 占比 (%) ==========")
dist_pct = dist.div(dist.sum(axis=1), axis=0).mul(100).round(1)
print(dist_pct)


# ========== 6. 合理性告警 ==========
print("\n========== 合理性告警 ==========")
flags = []
for plat, row in dist_pct.iterrows():
    for cat, pct in row.items():
        if cat in ["NA", "Other"]: 
            continue
        if pct > 40:
            flags.append(f"⚠️  [{plat}] {cat} 占比 {pct}% 过大，考虑拆分或调整优先级")
        elif 0 < pct < 1.5:
            flags.append(f"⚠️  [{plat}] {cat} 占比 {pct}% 过小，样本量不足")
    if row.get("Other", 0) > 8:
        flags.append(f"⚠️  [{plat}] Other 占比 {row['Other']}% 过大，关键词表可能漏了词")
    if row.get("NA", 0) > 70:
        flags.append(f"⚠️  [{plat}] NA 占比 {row['NA']}% 极大，该平台 category 分析需慎重")

if flags:
    for f in flags:
        print(f)
else:
    print("✅ 无异常")


# ========== 7. 人工抽查：每类看 15 条样本 ==========
print("\n========== 每类原始文本抽查（Instagram，每类 15 条）==========")
ig = big[big["_platform"] == "Instagram"]
for cat in ["Sports", "Beauty&Fashion", "Music", "Entertainment", 
            "Knowledge&Info", "Tech&Gaming", "Lifestyle", "Other"]:
    samples = ig[ig["category_unified"] == cat]["TOPIC OF INFLUENCE"] \
                .dropna().head(15).tolist()
    if samples:
        print(f"\n--- {cat} ({len(ig[ig['category_unified']==cat])} 人) ---")
        for s in samples:
            print(f"  • {s}")