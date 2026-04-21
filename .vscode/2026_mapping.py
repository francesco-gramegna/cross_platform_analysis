"""
2026 数据清洗：维基风格单值 category → 7 类
"""
import pandas as pd
from pathlib import Path

ROOT    = Path("/Users/pzy/Documents/DS Practice/data_raw")   # 改成你实际的根
OUT_DIR = ROOT 
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ========== 1. 2026 映射表（基于你实际数据的 37 个类别）==========
CATEGORY_MAP_2026 = {
    # ===== Entertainment =====
    "Entertainment":       "Entertainment",
    "Film":                "Entertainment",
    "Television program":  "Entertainment",
    "Humour":              "Entertainment",
    "Performing arts":     "Entertainment",
    
    # ===== Music =====
    "Music":                   "Music",
    "Pop music":               "Music",
    "Music of Asia":           "Music",
    "Electronic music":        "Music",
    "Hip hop music":           "Music",
    "Music of Latin America":  "Music",
    "Christian music":         "Music",
    "Soul music":              "Music",
    "Independent music":       "Music",     # ← 新增
    
    # ===== Tech&Gaming =====
    "Role-playing video game":    "Tech&Gaming",
    "Action game":                "Tech&Gaming",
    "Action-adventure game":      "Tech&Gaming",
    "Simulation video game":     "Tech&Gaming",
    "Casual game":                "Tech&Gaming",
    "Video game culture":         "Tech&Gaming",
    "Racing video game":          "Tech&Gaming",   # ← 新增
    "Technology":                 "Tech&Gaming",
    
    # ===== Knowledge&Info =====
    "Politics":   "Knowledge&Info",
    "Knowledge":  "Knowledge&Info",
    "Health":     "Knowledge&Info",
    "Education":  "Knowledge&Info",
    
    # ===== Sports =====
    "Sport":                 "Sports",
    "Association football":  "Sports",
    "Mixed martial arts":    "Sports",   # ← 新增
    "Physical fitness":      "Sports",   # ← 新增
    "Motorsport":            "Sports",   # ← 新增
    
    # ===== Lifestyle =====
    "Lifestyle (sociology)": "Lifestyle",
    "Society":               "Lifestyle",
    "Food":                  "Lifestyle",
    "Hobby":                 "Lifestyle",
    "Religion":              "Lifestyle",
    "Tourism":               "Lifestyle",   # ← 新增
    "Pet":                   "Lifestyle",   # ← 新增
}

# subcategory 也要同步更新
SUBCAT_MAP_2026 = {
    "Role-playing video game":    "Gaming",
    "Action game":                "Gaming",
    "Action-adventure game":      "Gaming",
    "Simulation video game":      "Gaming",
    "Casual game":                "Gaming",
    "Video game culture":         "Gaming",
    "Racing video game":          "Gaming",   # ← 新增
    "Technology":                 "Tech",
    "Education":                  "Education",
}

# ========== 2. 清洗流程 ==========
df = pd.read_csv(ROOT / "2026.csv")
n_raw = len(df)

# 2.1 保留 error 行单独保存（用于后续 survival 分析）
df_errors = df[df["status"] == "error"].copy()
df_errors.to_csv(OUT_DIR / "2026_errors.csv", index=False)
print(f"error 行: {len(df_errors)} 条，保存至 2026_errors.csv")

# 2.2 只保留 status=ok 的行做映射
df = df[df["status"] == "ok"].copy()
print(f"status=ok 行数: {len(df)}")

# 2.3 映射
df["category_primary"]  = df["category"]
df["category_unified"]  = df["category"].map(CATEGORY_MAP_2026)
df["subcategory"]       = df["category"].map(SUBCAT_MAP_2026)

# 未映射的原始类别记录下来（提醒补充映射表）
unmapped = df[df["category_primary"].notna() & df["category_unified"].isna()]
if len(unmapped) > 0:
    print(f"\n⚠️ 有 {len(unmapped)} 行原始类别未在映射表中:")
    print(unmapped["category_primary"].value_counts())

# 未映射 + NA 处理
df["category_unified"] = df["category_unified"].fillna(
    df["category_primary"].map(lambda x: "NA" if pd.isna(x) else "Other")
)

# 2.4 加标记列
df["_platform"] = "YouTube"
df["_year"]     = 2026


# ========== 3. 输出报告 ==========
print("\n========== 2026 映射质量报告 ==========")
total_valid = len(df)
n_na     = (df["category_unified"] == "NA").sum()
n_other  = (df["category_unified"] == "Other").sum()
n_mapped = total_valid - n_na - n_other

print(f"  有效行: {total_valid}")
print(f"  成功映射: {n_mapped} ({n_mapped/total_valid:.1%})")
print(f"  NA: {n_na} ({n_na/total_valid:.1%})")
print(f"  Other: {n_other} ({n_other/total_valid:.1%})")

# 相对整个原始数据集的有效率
print(f"\n  相对原始 {n_raw} 行:")
print(f"  可用样本 {total_valid} ({total_valid/n_raw:.1%}) "
      f"— error 行已被剔除")

print("\n========== 7 类分布 ==========")
dist = df["category_unified"].value_counts()
print(dist)
print("\n占比 (%):")
print((dist / total_valid * 100).round(1))


# ========== 4. 保存 ==========
df.to_csv(OUT_DIR / "merged_2026.csv", index=False, encoding="utf-8-sig")
print(f"\n已保存: merged_2026.csv ({len(df)} 行)")


# ========== 5. 合理性告警 ==========
print("\n========== 合理性告警 ==========")
flags = []
for cat, n in dist.items():
    pct = n / total_valid * 100
    if cat in ["NA", "Other"]:
        if pct > 5:
            flags.append(f"⚠️ {cat} 占比 {pct:.1f}% 偏高")
    elif pct > 40:
        flags.append(f"⚠️ {cat} 占比 {pct:.1f}% 过大")
    elif pct < 2:
        flags.append(f"⚠️ {cat} 占比 {pct:.1f}% 过小，样本不足")

# Beauty&Fashion 缺失的说明
if "Beauty&Fashion" not in dist.index:
    flags.append("ℹ️  Beauty&Fashion 类无样本（2026 YouTube 爬虫数据中无该类影响者）")

# 样本量告警
if total_valid < 300:
    flags.append(f"⚠️ 有效样本仅 {total_valid} 条，RQ2a 的 7 类卡方可能因 cell 期望频数 < 5 而失效")

if flags:
    for f in flags:
        print(f)
else:
    print("✅ 无异常")