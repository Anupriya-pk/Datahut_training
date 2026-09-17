

import csv
import json

from settings_sample import OUTPUT_FILE


INPUT_FILE = "parsed_products.json"


FIELDS = [
    "product_id",
    "product_name",
    "brand",
    "price",
    "currency",
    "colour",
    "product_code",
    "description",
    "composition",
    "fit",
    "image",
    "product_url",
]


def load_products():

    try:

        with open(
            INPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except FileNotFoundError:

        print(
            f"{INPUT_FILE} not found."
        )

        return []


def export_csv(products):

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FIELDS,
            extrasaction="ignore"
        )

        writer.writeheader()

        for product in products:

            writer.writerow(product)


def main():

    products = load_products()

    if not products:

        print(
            "No products to export."
        )

        return

    export_csv(products)

    print()
    print("=" * 70)
    print("EXPORT COMPLETED")
    print("=" * 70)
    print(
        "TOTAL PRODUCTS:",
        len(products)
    )
    print(
        "CSV FILE:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()