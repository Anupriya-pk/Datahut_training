import csv

def export_items(items, filename="output.csv"):

    fields = [
        "url",
        "title",
        "price",
        "location",
        "bedrooms",
        "bathrooms",
        "area"
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(f, fieldnames=fields)

        writer.writeheader()

        for item in items:
            writer.writerow(item.to_dict())