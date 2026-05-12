import csv

def dedupe_csv_inplace(file_path):
    seen = set()
    unique_rows = []
    duplicates = []

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        unique_rows.append(header)

        for row in reader:
            row_tuple = tuple(row)
            if row_tuple in seen:
                duplicates.append(row)
                print("Deleting duplicate row:", row)
            else:
                seen.add(row_tuple)
                unique_rows.append(row)

    print(f"Found {len(duplicates)} duplicate rows.")

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(unique_rows)

    print("Done.")


# usage
dedupe_csv_inplace("3 - handles merging/preprocessedData.csv")
