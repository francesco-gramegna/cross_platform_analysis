"""
2022 数据清洗：只用 Category_1，映射到 7 类统一标签
输入：2022/ 目录下的 10 个 CSV（IG 5 个月 + YT 5 个月）
输出：eda_output/ 下的清洗结果 + 质量报告
"""
import pandas as pd
import numpy as np
from pathlib import Path

# ========== 0. 路径 ==========
ROOT = Path("/Users/pzy/Documents/DS Practice/data_raw")   # 改成你实际的根
DIR_2022 = ROOT / "2022"
OUT_DIR  = ROOT / "2022_output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ========== 1. 2022 映射表（基于真实频数设计）==========
# 原则：
#   - 样本 >= 10 的原始类别都能找到合适的 7 类归属
#   - 语义明确的单独类目保留（Adult content、Cars 等）并归入 Other
#   - 跨平台一致：IG 和 YT 共用同一份映射
CATEGORY_MAP_2022 = {
    # ===== Entertainment =====
    "Cinema & Actors/actresses": "Entertainment",
    "Shows": "Entertainment",
    "Humor & Fun & Happiness": "Entertainment",
    "Movies": "Entertainment",
    "Animation": "Entertainment",
    "Humor": "Entertainment",

    # ===== Music =====
    "Music": "Music",
    "Music & Dance": "Music",

    # ===== Sports =====
    "Sports with a ball": "Sports",
    "Sports": "Sports",
    "Fitness & Gym": "Sports",
    "Fitness": "Sports",
    "Racing Sports": "Sports",
    "Winter sports": "Sports",
    "Water sports": "Sports",
    "Extreme Sports & Outdoor activity": "Sports",

    # ===== Beauty&Fashion =====
    "Beauty": "Beauty&Fashion",
    "Fashion": "Beauty&Fashion",
    "Modeling": "Beauty&Fashion",
    "Clothing & Outfits": "Beauty&Fashion",
    "Accessories & Jewellery": "Beauty&Fashion",
    "Luxury": "Beauty&Fashion",

    # ===== Tech&Gaming =====
    "Gaming": "Tech&Gaming",
    "Video games": "Tech&Gaming",
    "Computers & Gadgets": "Tech&Gaming",
    "Machinery & Technologies": "Tech&Gaming",
    "Science & Technology": "Tech&Gaming",
    "Science": "Tech&Gaming",
    "Crypto": "Tech&Gaming",

    # ===== Info&Business =====
    "News & Politics": "Knowledge&Info",
    "Education": "Knowledge&Info",
    "Finance & Economics": "Knowledge&Info",
    "Business & Careers": "Knowledge&Info",
    "Management & Marketing": "Knowledge&Info",
    "Literature & Journalism": "Knowledge&Info",
    "Health & Self Help": "Knowledge&Info",

    # ===== Lifestyle =====
    "Lifestyle": "Lifestyle",
    "Daily vlogs": "Lifestyle",
    "Family": "Lifestyle",
    "Food & Cooking": "Lifestyle",
    "Food & Drinks": "Lifestyle",
    "Travel": "Lifestyle",
    "Animals": "Lifestyle",
    "Animals & Pets": "Lifestyle",
    "Photography": "Lifestyle",
    "Nature & landscapes": "Lifestyle",
    "Art/Artists": "Lifestyle",
    "Design/art": "Lifestyle",
    "DIY & Design": "Lifestyle",
    "DIY & Life Hacks": "Lifestyle",
    "ASMR": "Lifestyle",
    "Toys": "Lifestyle",
    "Kids & Toys": "Lifestyle",

    # ===== Other（语义不适合任何 7 类）=====
    "Adult content": "Other",
    "Cars & Motorbikes": "Other",
    "Autos & Vehicles": "Other",
    "Mystery": "Other",
}
SUBCAT_MAP_2022 = {
    # Tech / Gaming 拆分
    "Gaming":                  "Gaming",
    "Video games":             "Gaming",
    "Computers & Gadgets":     "Tech",
    "Science & Technology":    "Tech",
    "Science":                 "Tech",
    "Machinery & Technologies":"Tech",
    "Crypto":                  "Tech",
    # 其他类暂时不细分（保留空）
}


# ========== 2. 工具函数 ==========
def parse_filename(fname):
    """从文件名提取平台和月份"""
    f = fname.lower()
    platform = ("Instagram" if "instagram" in f else
                "YouTube"   if "youtube"   in f else
                "TikTok"    if "tiktok"    in f else "Unknown")
    for m in ["june", "sep", "nov", "dec", "mar"]:
        if m in f:
            return platform, m
    return platform, "unknown"


def find_c1_col(df):
    """找 Category_1 列（大小写/下划线/横杠都兼容）"""
    for col in df.columns:
        c = col.strip().lower().replace("_", "").replace("-", "").replace(" ", "")
        if "category" in c and "1" in c:
            return col
    # 有些文件就叫 "Category"（没有数字后缀）
    for col in df.columns:
        if col.strip().lower() == "category":
            return col
    return None


# ========== 3. 主流程 ==========
all_data = []
mapping_report = []  # 记录映射情况

for csv_path in sorted(DIR_2022.glob("*.csv")):
    platform, month = parse_filename(csv_path.name)

    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="latin-1")

    n_total = len(df)
    c1_col = find_c1_col(df)

    # TikTok 没有 category，跳过类别映射但记录
    if c1_col is None:
        print(f"[{platform} {month}] 无 Category 列，跳过映射")
        continue

    # 做映射
    raw = df[c1_col]
    mapped = raw.map(CATEGORY_MAP_2022)

    # 分类每行的状态
    status = pd.Series(index=df.index, dtype=object)
    status[raw.isna()] = "NA"                                      # 原始缺失
    status[raw.notna() & mapped.notna()] = "MAPPED"                # 成功映射
    status[raw.notna() & mapped.isna()] = "UNMAPPED"               # 映射表里没有

    # 未映射的原始类别记下来（提醒补充映射表）
    unmapped_cats = raw[status == "UNMAPPED"].value_counts()
    if len(unmapped_cats) > 0:
        print(f"\n⚠️ [{platform} {month}] 有 {status.eq('UNMAPPED').sum()} 行无法映射:")
        for c, n in unmapped_cats.items():
            print(f"    {c}: {n}")

    # category_unified：未映射的标为 "Other"，NA 标为 "NA"
    df["category_primary"]  = raw
    df["category_unified"]  = mapped.fillna(
        status.map({"NA": "NA", "UNMAPPED": "Other", "MAPPED": None})
    )
    # 3) 在主流程里生成 subcategory
    df["subcategory"] = df["category_primary"].map(SUBCAT_MAP_2022)

    df["_platform"] = platform
    df["_month"]    = month
    df["_year"]     = 2022

    # 统计
    mapping_report.append({
        "platform": platform,
        "month":    month,
        "n_total":  n_total,
        "n_na":     (status == "NA").sum(),
        "n_mapped": (status == "MAPPED").sum(),
        "n_unmapped": (status == "UNMAPPED").sum(),
        "na_rate":  round((status == "NA").sum() / n_total, 3),
        "unmapped_rate": round((status == "UNMAPPED").sum() / n_total, 3),
    })

    all_data.append(df)


# ========== 4. 保存结果 ==========
report_df = pd.DataFrame(mapping_report)
print("\n========== 映射质量报告 ==========")
print(report_df.to_string(index=False))
report_df.to_csv(OUT_DIR / "merge_2022_report.csv", index=False)


# ========== 5. 合理性检查 ==========
if all_data:
    big = pd.concat(all_data, ignore_index=True, sort=False)
    big.to_csv(OUT_DIR / "merged_2022_all.csv", index=False)
    print(f"\n合并后总行数: {len(big)}, 保存至 merged_2022_all.csv")

    # 检查 1: 每个 (platform, month) 的 7 类分布
    print("\n========== 7 类分布（按 平台 × 月份）==========")
    dist = big.groupby(["_platform", "_month", "category_unified"]).size().unstack(fill_value=0)
    print(dist)

    # 检查 2: 占比
    print("\n========== 占比 (%) ==========")
    dist_pct = dist.div(dist.sum(axis=1), axis=0).mul(100).round(1)
    print(dist_pct)

    # 检查 3: 告警
    print("\n========== 合理性告警 ==========")
    flags = []
    for idx, row in dist_pct.iterrows():
        plat, month = idx
        for cat, pct in row.items():
            if cat in ["NA", "Other"]:
                continue
            if pct > 35:
                flags.append(f"⚠️ [{plat} {month}] {cat} 占比 {pct}% 过大（可能是垃圾桶）")
            elif 0 < pct < 2:
                flags.append(f"⚠️ [{plat} {month}] {cat} 占比 {pct}% 过小（样本不足）")
        if row.get("Other", 0) > 5:
            flags.append(f"⚠️ [{plat} {month}] Other 占比 {row['Other']}% > 5%（映射表可能不全）")

    if flags:
        for f in flags:
            print(f)
    else:
        print("✅ 无异常")