import csv
import os

# List of your files (add .csv if needed)
files = [
    "instagram_december",
    "instagram_june",
    "instagram_march",
    "instagram_november",
    "instagram_september",
    "tiktok_december",
    "tiktok_june",
    "tiktok_march",
    "tiktok_november",
    "tiktok_september",
    "youtube_december",
    "youtube_june",
    "youtube_march",
    "youtube_november",
    "youtube_september"
]

for file in files:
    try:
        with open('crude_dataset/kaggle_2022/' + file, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)  # first row (fields)

            print(f"\n📄 {file}")
            print("-" * 40)
            for h in headers:
                print(h)

    except FileNotFoundError:
        print(f"\n❌ {file} not found")
    except Exception as e:
        print(f"\n⚠️ Error reading {file}: {e}")
