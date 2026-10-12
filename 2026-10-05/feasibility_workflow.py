#  CRAWLER
import csv
import re
from urllib.parse import urlparse, quote_plus
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.zalando.co.uk"
KEYWORD = "Mini dress"
MAX_PRODUCTS = 10
OUTPUT_FILE = "zalando_product_urls.csv"

SEARCH_URL = BASE_URL + "/women/?q=" + quote_plus(KEYWORD)


def collect_product_urls(page):
    links = page.locator("a[href]").evaluate_all("""
        elements => elements.map(a => {
            const r = a.getBoundingClientRect();
            const s = getComputedStyle(a);

            return {
                href: a.href,
                top: r.top + window.scrollY,
                left: r.left + window.scrollX,
                width: r.width,
                height: r.height,
                display: s.display,
                visibility: s.visibility
            };
        })
    """)

    products = {}

    for item in links:
        parsed = urlparse(item["href"])

        if parsed.netloc.lower() not in (
            "www.zalando.co.uk", "zalando.co.uk"
        ):
            continue

        if not re.search(
            r"-[a-z0-9]{9}-[a-z0-9]{3}\.html$",
            parsed.path,
            re.I
        ):
            continue

        if (
            item["width"] <= 0
            or item["height"] <= 0
            or item["display"] == "none"
            or item["visibility"] == "hidden"
        ):
            continue

        url = "https://www.zalando.co.uk" + parsed.path
        position = (item["top"], item["left"])

        if url not in products or position < products[url]:
            products[url] = position

    sorted_products = sorted(
        products.items(),
        key=lambda item: item[1]
    )

    return [url for url, position in sorted_products]


def main():
    try:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=False)
            page = browser.new_page(
                viewport={"width": 1366, "height": 768},
                locale="en-GB"
            )

            page.goto(
                BASE_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.goto(
                SEARCH_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(5000)

            product_urls = []

            for _ in range(5):
                product_urls = collect_product_urls(page)

                if len(product_urls) >= MAX_PRODUCTS:
                    break

                page.evaluate(
                    "window.scrollBy(0, window.innerHeight * 0.8)"
                )
                page.wait_for_timeout(2000)

            top_products = product_urls[:MAX_PRODUCTS]

            if top_products:
                with open(
                    OUTPUT_FILE,
                    "w",
                    newline="",
                    encoding="utf-8-sig"
                ) as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        "keyword", "rank", "product_url"
                    ])

                    for rank, url in enumerate(top_products, 1):
                        writer.writerow([KEYWORD, rank, url])

                print(
                    f"{len(top_products)} product URLs saved to "
                    f"{OUTPUT_FILE}"
                )
            else:
                print("No product URLs found. CSV not saved.")

            browser.close()

    except Exception:
        print("Crawling failed. Check website access and try again.")


if __name__ == "__main__":
    main()

# # ***********************************************************

# # PARSER

import csv
import json
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright
from parsel import Selector


# ================= CONFIGURATION =================

URL = (
    "https://www.zalando.co.uk/"
    "vero-moda-party-dress-awelliana-short-dress-"
    "cocktail-dressparty-dress-black-ve121c5ds-q11.html"
)

KEYWORD = "Mini dress"
RANK = 1

OUTPUT_FILE = "zalando_parser_example.csv"

FIELDS = [
    "product_name",
    "brand",
    "unique_id",
    "product_description",
    "product_type",
    "price",
    "image_url_1",
    "pdp_url",
    "gender",
    "occasion/style tags",
    "rank",
    "color",
    "size",
]


# ================= HELPER FUNCTIONS =================

def clean(value):
    if value is None:
        return ""

    return " ".join(str(value).split())


def get_text(selector, xpath):
    return clean(selector.xpath(xpath).get(default=""))


# ================= EXTRACT JSON-LD =================

def find_product_data(selector):
    products = []
    product_groups = []

    scripts = selector.xpath(
        '//script[@type="application/ld+json"]/text()'
    ).getall()

    def search(data):
        if isinstance(data, list):
            for item in data:
                search(item)

        elif isinstance(data, dict):
            item_type = data.get("@type", [])

            if isinstance(item_type, str):
                item_type = [item_type]

            if "Product" in item_type:
                products.append(data)

            elif "ProductGroup" in item_type:
                product_groups.append(data)

            for value in data.values():
                if isinstance(value, (dict, list)):
                    search(value)

    for script in scripts:
        try:
            data = json.loads(script)
            search(data)

        except (json.JSONDecodeError, TypeError):
            continue

    if products:
        return products[0], products, product_groups

    if product_groups:
        return product_groups[0], products, product_groups

    return {}, products, product_groups


# ================= BRAND =================

def get_brand(product, selector):
    brand = product.get("brand", "")

    if isinstance(brand, dict):
        brand = brand.get("name", "")

    if brand:
        return clean(brand)

    return get_text(
        selector,
        '//meta[@property="product:brand"]/@content'
        ' | //meta[@name="brand"]/@content'
    )


# ================= UNIQUE ID =================

def get_unique_id(product):
    unique_id = (
        product.get("sku")
        or product.get("productID")
        or product.get("mpn")
    )

    return clean(unique_id)


# ================= DESCRIPTION =================

def get_description(product, selector):
    description = product.get("description", "")

    if description:
        return clean(description)

    return get_text(
        selector,
        '//meta[@name="description"]/@content'
        ' | //meta[@property="og:description"]/@content'
    )


# ================= PRODUCT TYPE =================

def get_product_type(product, selector):
    product_type = product.get("category", "")

    if isinstance(product_type, list):
        product_type = " > ".join(
            str(item) for item in product_type
        )

    if product_type:
        return clean(product_type)

    # Use the product name as a fallback.
    name = (
        product.get("name", "")
        or get_text(selector, "//h1//text()")
    ).lower()

    # The task's broad product type is determined by the keyword.
    keyword = KEYWORD.lower()

    if "dress" in keyword or "dress" in name:
        return "Dress"

    if "jeans" in keyword or "jeans" in name:
        return "Jeans"

    if "cardigan" in keyword or "cardigan" in name:
        return "Cardigan"

    if "jumper" in keyword or "jumper" in name:
        return "Jumper"

    if "knitwear" in keyword or "knitwear" in name:
        return "Knitwear"

    if "top" in keyword or "top" in name:
        return "Top"

    return ""


# ================= PRICE =================

def get_price(product, selector):
    offers = product.get("offers", {})

    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    if not isinstance(offers, dict):
        offers = {}

    price = (
        offers.get("price")
        or offers.get("lowPrice")
        or get_text(
            selector,
            '//meta[@property="product:price:amount"]/@content'
            ' | //meta[@itemprop="price"]/@content'
        )
    )

    currency = (
        offers.get("priceCurrency")
        or get_text(
            selector,
            '//meta[@property="product:price:currency"]/@content'
        )
    )

    if price and currency:
        return str(price) + " " + str(currency)

    return clean(price)


# ================= MAIN IMAGE =================

def get_image(product, selector):
    image = product.get("image", "")

    if isinstance(image, list):
        image = image[0] if image else ""

    if isinstance(image, dict):
        image = image.get("url", "")

    if not image:
        image = get_text(
            selector,
            '//meta[@property="og:image"]/@content'
            ' | //meta[@name="twitter:image"]/@content'
        )

    if image:
        return urljoin(URL, image)

    return ""


# ================= COLOUR =================

def get_colour(product, selector):
    colour = product.get("color", "")

    if isinstance(colour, dict):
        colour = colour.get("name", "")

    if colour:
        return clean(colour)

    # Check structured product properties.
    properties = product.get("additionalProperty", [])

    if isinstance(properties, dict):
        properties = [properties]

    for item in properties:
        if not isinstance(item, dict):
            continue

        property_name = clean(item.get("name", "")).lower()

        if property_name in ["color", "colour"]:
            return clean(item.get("value", ""))

    # Check HTML metadata and colour-related attributes.
    return get_text(
        selector,
        '//meta[@property="product:color"]/@content'
        ' | //*[@data-testid="color-selector"]/@aria-label'
        ' | //*[@data-testid="color-option"]/@aria-label'
    )


# ================= SIZE =================

def get_sizes(selector, products, product_groups):
    sizes = []

    # First, extract sizes from structured product data.
    all_products = products + product_groups

    for product in all_products:
        size = product.get("size")

        if isinstance(size, str) and size.strip():
            size = clean(size)

            if size not in sizes:
                sizes.append(size)

        variants = product.get("hasVariant", [])

        if isinstance(variants, dict):
            variants = [variants]

        for variant in variants:
            if not isinstance(variant, dict):
                continue

            variant_size = variant.get("size", "")

            if isinstance(variant_size, str) and variant_size.strip():
                variant_size = clean(variant_size)

                if variant_size not in sizes:
                    sizes.append(variant_size)

    # Extract size options from the rendered HTML using XPath.
    size_texts = selector.xpath(
        '//*[@data-testid="size-selector"]//button//text()'
        ' | //*[@data-testid="size-option"]//text()'
        ' | //select[contains(@name, "size")]/option/text()'
        ' | //button[contains(@aria-label, "size")]/@aria-label'
    ).getall()

    for value in size_texts:
        value = clean(value)

        if value and value not in sizes:
            sizes.append(value)

    return " | ".join(sizes)


# ================= GENDER =================

def get_gender(product, selector):
    gender = product.get("gender", "")

    if isinstance(gender, dict):
        gender = gender.get("name", "")

    if isinstance(gender, list):
        gender = " | ".join(str(item) for item in gender)

    if gender:
        return clean(gender)

    gender = get_text(
        selector,
        '//meta[@property="product:gender"]/@content'
    )

    if gender:
        return gender

    # This task specifically targets women's clothing.
    return "Women"


# ================= OCCASION / STYLE TAGS =================

def get_occasion_tags(product):
    tags = []

    properties = product.get("additionalProperty", [])

    if isinstance(properties, dict):
        properties = [properties]

    for item in properties:
        if not isinstance(item, dict):
            continue

        property_name = clean(item.get("name", "")).lower()

        if "occasion" in property_name or "style" in property_name:
            value = clean(item.get("value", ""))

            if value and value not in tags:
                tags.append(value)

    return " | ".join(tags)


# ================= MAIN PARSER =================

def main():
    browser = None

    try:
        with sync_playwright() as playwright:

            browser = playwright.firefox.launch(
                headless=False
            )

            page = browser.new_page(
                locale="en-GB",
                viewport={
                    "width": 1366,
                    "height": 768
                }
            )

            response = page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            if response and response.status >= 400:
                print("Product page failed:", response.status)
                return

            page.wait_for_timeout(4000)

            # Get the rendered HTML.
            html = page.content()

            # Parse using Parsel Selector.
            selector = Selector(text=html)

            # Extract structured product data.
            product, products, product_groups = find_product_data(
                selector
            )

            # Extract the required fields.
            product_name = (
                product.get("name", "")
                or get_text(selector, "//h1//text()")
                or get_text(
                    selector,
                    '//meta[@property="og:title"]/@content'
                )
            )

            brand = get_brand(product, selector)

            unique_id = get_unique_id(product)

            description = get_description(product, selector)

            product_type = get_product_type(
                product,
                selector
            )

            price = get_price(product, selector)

            image_url = get_image(product, selector)

            colour = get_colour(product, selector)

            gender = get_gender(product, selector)

            size = get_sizes(
                selector,
                products,
                product_groups
            )

            occasion_tags = get_occasion_tags(product)

            # Prepare the final row.
            result = {
                "product_name": clean(product_name),
                "brand": clean(brand),
                "unique_id": unique_id,
                "product_description": clean(description),
                "product_type": clean(product_type),
                "price": price,
                "image_url_1": image_url,
                "pdp_url": URL,
                "gender": gender,
                "occasion/style tags": occasion_tags,
                "rank": RANK,
                "color": clean(colour),
                "size": size
            }

            browser.close()
            browser = None

    except Exception as error:
        print("Parser failed:", error)
        return

    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass

    # Save the extracted data to CSV.
    try:
        with open(
            OUTPUT_FILE,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=FIELDS
            )

            writer.writeheader()
            writer.writerow(result)

        print("Parser data saved to", OUTPUT_FILE)

    except OSError as error:
        print("CSV save failed:", error)


if __name__ == "__main__":
    main()