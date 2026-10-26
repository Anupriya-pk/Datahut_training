import re
import csv
import logging
from html import unescape
from re import sub
from settings import FILE_NAME_FULLDUMP, CSV_DELIMITER, COMPETITOR_NAME, EXTRACTION_DATE, CURRENCY
from items import ProductItem

csv_headers = [
    "dh_unique_id",
    "dh_unique_id_b64",
    "unique_id",
    "competitor_name",
    "store_name",
    "store_addressline1",
    "store_addressline2",
    "store_suburb",
    "store_state",
    "store_postcode",
    "store_addressid",
    "extraction_date",
    "product_name",
    "brand",
    "brand_type",
    "grammage_quantity",
    "netcontent",
    "netweight",
    "grammage_unit",
    "drained_weight",
    "producthierarchy_level1",
    "producthierarchy_level2",
    "producthierarchy_level3",
    "producthierarchy_level4",
    "producthierarchy_level5",
    "producthierarchy_level6",
    "producthierarchy_level7",
    "regular_price",
    "selling_price",
    "promotion_price",
    "promotion_valid_from",
    "promotion_valid_upto",
    "promotion_type",
    "percentage_discount",
    "promotion_description",
    "price_was",
    "package_sizeof_sellingprice",
    "per_unit_sizedescription",
    "price_valid_from",
    "price_per_unit",
    "multi_buy_item_count",
    "multi_buy_items_price_total",
    "currency",
    "breadcrumb",
    "pdp_url",
    "variants",
    "product_description",
    "ingredients",
    "country_of_origin",
    "allergens",
    "age_of_the_product",
    "age_recommendations",
    "instructions",
    "storage_instructions",
    "preparationinstructions",
    "instructionforuse",
    "nutritional_information",
    "nutritions",
    "flavour",
    "vitamins",
    "labelling",
    "grade",
    "region",
    "packaging",
    "receipies",
    "processed_food",
    "barcode",
    "frozen",
    "chilled",
    "organictype",
    "cooking_part",
    "handmade",
    "max_heating_temperature",
    "special_information",
    "label_information",
    "dimensions",
    "special_nutrition_purpose",
    "feeding_recommendation",
    "warranty",
    "color",
    "model_number",
    "material",
    "usp",
    "dosage_recommendation",
    "tasting_note",
    "food_preservation",
    "size",
    "rating",
    "review",
    "file_name_1",
    "image_url_1",
    "file_name_2",
    "image_url_2",
    "file_name_3",
    "image_url_3",
    "file_name_4",
    "image_url_4",
    "file_name_5",
    "image_url_5",
    "file_name_6",
    "image_url_6",
    "competitor_product_key",
    "fit_guide",
    "occasion",
    "material_composition",
    "style",
    "care_instructions",
    "heel_type",
    "heel_height",
    "upc",
    "features",
    "dietary_lifestyle",
    "manufacturer_address",
    "importer_address",
    "distributor_address",
    "vinification_details",
    "recycling_information",
    "return_address",
    "alchol_by_volume",
    "beer_deg",
    "gender",
    "clothing_type",
    "clothing_fit",
    "clothing_length",
    "collar_type",
    "pattern",
    "pocket",
    "fastener_closure_type",
    "rise_pants_capris",
    "pant_leg_cut",
    "iron",
    "stretch",
    "maternity",
    "thermal",
    "clothing_weight",
    "upper_body_strap_configuration",
    "clothing_leg_bottom_opening_style",
    "cuffs_style",
    "back_style",
    "neck_style",
    "clothing_length_style",
    "sleeve_length_style",
    "ean",
    "product_type",
    "body_fit",
    "range",
    "variant_color"
]

GENDER_MAP = {
    "womens": "Women", "mens": "Men", "boys": "Boys", "girls": "Girls", "baby": "Baby",
}


class Export:
    """PostProcessing - Export to CSV"""

    def __init__(self, writer):
        self.writer = writer

    def start(self):
        """Start Function"""

        self.writer.writerow(csv_headers)
        logging.info(csv_headers)

        count = 0
        for item in ProductItem.load():

            # every column defaults to '' (same as the blank variables in the sample export)
            row = {header: "" for header in csv_headers}

            product_code = item.get("product_code", "")
            category = item.get("category", "") or ""
            parts = [p for p in category.split("/shop/")[-1].split("/") if p]  # womens/clothing

            breadcrumb = item.get("breadcrumbs", "")
            levels = [x.strip() for x in breadcrumb.split(">") if x.strip()] if breadcrumb else []
            if levels and levels[0].lower() in ("home", "next"):
                levels = levels[1:]
            if not levels:
                levels = [p.replace("-", " ").title() for p in parts]

            selling_price = self.clean_price(item.get("price", ""))
            regular_price = self.clean_price(item.get("regular_price", "")) or selling_price
            promotion_price = selling_price if regular_price != selling_price else ""

            description = sub(r"<.*?>|\s+", " ", unescape(item.get("description", "") or "")).strip()
            sizes = item.get("sizes") or []
            images = item.get("images") or []

            row.update({
                "unique_id": product_code,
                "competitor_name": COMPETITOR_NAME,
                "extraction_date": EXTRACTION_DATE,
                "product_name": item.get("product_name", ""),
                "brand": item.get("brand", "") or "Next",
                "regular_price": regular_price,
                "selling_price": selling_price,
                "promotion_price": promotion_price,
                "currency": item.get("currency", "") or CURRENCY,
                "breadcrumb": breadcrumb,
                "pdp_url": item.get("url", ""),
                "variants": ",".join(sizes),
                "size": ",".join(sizes),
                "product_description": description,
                "color": item.get("color", ""),
                "model_number": product_code,
                "rating": "" if item.get("rating") in ("0", 0) else item.get("rating", ""),
                "review": "" if item.get("review") in ("0", 0) else item.get("review", ""),
                "competitor_product_key": product_code,
                "gender": GENDER_MAP.get(parts[0], "") if parts else "",
                "material_composition": self.pick_sentence(description, r"\d+\s?%"),
                "care_instructions": self.pick_sentence(description, r"wash|dry clean|tumble|iron"),
                "variant_color": item.get("color", ""),
            })
            for index in range(6):
                if index < len(images):
                    row[f"file_name_{index + 1}"] = images[index].split("/")[-1]
                    row[f"image_url_{index + 1}"] = images[index]
            for index in range(7):
                if index < len(levels):
                    row[f"producthierarchy_level{index + 1}"] = levels[index]

            data = [row[header] for header in csv_headers]
            self.writer.writerow(data)
            logging.info(dict(zip(csv_headers, data)))
            count += 1

        logging.info(f"Rows exported: {count} -> {FILE_NAME_FULLDUMP}")

    @staticmethod
    def clean_price(value):
        value = str(value or "").replace("£", "").replace(",", "").strip()
        try:
            return format(float(value), ".2f") if value else ""
        except ValueError:
            return ""

    @staticmethod
    def pick_sentence(text, pattern):
        """Join the sentences of a description that match a regex"""
        found = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if re.search(pattern, s, re.I)]
        return " ".join(found)

    def clean_string(self, input_string):

        cleaned_string = re.sub(r'[^A-Za-z0-9]', '', input_string)
        return cleaned_string


if __name__ == "__main__":
    with open(FILE_NAME_FULLDUMP, "w", encoding="utf-8", newline="") as file:
        writer_file = csv.writer(file, delimiter=CSV_DELIMITER, quotechar='"')

        export = Export(writer_file)
        export.start()