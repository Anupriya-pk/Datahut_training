

import json
import re

from playwright.sync_api import sync_playwright, TimeoutError
from parsel import Selector


# ==========================================================
# URLS
# ==========================================================

URL = (
    "https://www.johnlewis.com/"
    "mint-velvet-animal-print-ruffle-mini-dress-brown/"
    "p115731686"
)

SEARCH_URL = (
    "https://www.johnlewis.com/"
    "search?search-term=mini+dress"
)


# ==========================================================
# CLEAN TEXT
# ==========================================================

def clean(text):

    if not text:
        return ""

    return " ".join(text.split())


# ==========================================================
# JSON-LD
# ==========================================================

def get_jsonld(selector):

    products = []

    scripts = selector.css(
        'script[type="application/ld+json"]::text'
    ).getall()

    for script in scripts:

        try:

            data = json.loads(script)

            # Dictionary
            if isinstance(data, dict):

                if data.get("@type") == "Product":
                    products.append(data)

                graph = data.get("@graph", [])

                if isinstance(graph, list):

                    for item in graph:

                        if not isinstance(item, dict):
                            continue

                        item_type = item.get("@type")

                        if item_type == "Product":

                            products.append(item)

                        elif isinstance(item_type, list):

                            if "Product" in item_type:
                                products.append(item)

            # List
            elif isinstance(data, list):

                for item in data:

                    if not isinstance(item, dict):
                        continue

                    item_type = item.get("@type")

                    if item_type == "Product":

                        products.append(item)

                    elif isinstance(item_type, list):

                        if "Product" in item_type:
                            products.append(item)

        except Exception:
            continue

    return products[0] if products else {}


# ==========================================================
# GET PRODUCT RANK
# ==========================================================

def get_product_rank(search_url, product_url):

    print()
    print("=" * 90)
    print("CHECKING SEARCH RESULT RANK")
    print("=" * 90)

    print("Search URL:", search_url)

    # Product ID from the PDP URL
    target_match = re.search(
        r"/p(\d+)",
        product_url
    )

    if not target_match:

        print("Could not find target product ID")

        return ""

    target_product_id = target_match.group(1)

    print(
        "Target Product ID:",
        target_product_id
    )

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page(
            viewport={
                "width": 1366,
                "height": 768
            }
        )

        try:

            response = page.goto(
                search_url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            if response:

                print(
                    "Search HTTP Status:",
                    response.status
                )

            # Wait for JavaScript
            page.wait_for_timeout(5000)

            # --------------------------------------------------
            # SCROLL TO LOAD PRODUCTS
            # --------------------------------------------------

            for i in range(5):

                page.mouse.wheel(
                    0,
                    1500
                )

                page.wait_for_timeout(1500)

            # Go back to top
            page.evaluate(
                "window.scrollTo(0, 0)"
            )

            page.wait_for_timeout(2000)

            # --------------------------------------------------
            # GET ALL LINKS
            # --------------------------------------------------

            links = page.locator(
                "a"
            ).evaluate_all("""
                elements => elements.map(a => a.href)
            """)

            product_urls = []
            product_ids = []

            # --------------------------------------------------
            # EXTRACT PRODUCT LINKS
            # --------------------------------------------------

            for link in links:

                if not link:
                    continue

                # Find John Lewis product ID
                match = re.search(
                    r"/p(\d+)(?:[/?#]|$)",
                    link
                )

                if not match:
                    continue

                product_id = match.group(1)

                # Avoid duplicate product IDs
                if product_id in product_ids:
                    continue

                clean_url = (
                    link
                    .split("?")[0]
                    .split("#")[0]
                    .rstrip("/")
                )

                product_ids.append(
                    product_id
                )

                product_urls.append(
                    clean_url
                )

            print()
            print(
                "Product URLs found:",
                len(product_urls)
            )

            # --------------------------------------------------
            # TOP 10
            # --------------------------------------------------

            print()
            print("TOP 10 SEARCH RESULTS")
            print("-" * 90)

            for rank, item_url in enumerate(
                product_urls[:10],
                start=1
            ):

                print(
                    f"{rank}. {item_url}"
                )

            # --------------------------------------------------
            # FIND TARGET PRODUCT
            # --------------------------------------------------

            if target_product_id in product_ids:

                rank = (
                    product_ids.index(
                        target_product_id
                    )
                    + 1
                )

                print()
                print(
                    "PRODUCT FOUND"
                )

                print(
                    "Target Product ID:",
                    target_product_id
                )

                print(
                    "PRODUCT RANK:",
                    rank
                )

                return rank

            else:

                print()
                print(
                    "PRODUCT NOT FOUND IN SEARCH RESULTS"
                )

                print(
                    "Target Product ID:",
                    target_product_id
                )

                return ""

        except TimeoutError:

            print(
                "Search page TIMEOUT"
            )

            return ""

        except Exception as e:

            print(
                "Rank checking FAILED"
            )

            print(
                "ERROR:",
                e
            )

            return ""

        finally:

            browser.close()

# ==========================================================
# PRODUCT PARSER
# ==========================================================

def extract_product(url, rank):

    print()
    print("=" * 90)
    print("LOADING PRODUCT PAGE")
    print("=" * 90)

    print("PDP URL:", url)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page(
            viewport={
                "width": 1366,
                "height": 768
            }
        )

        try:

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            if response is None:

                print(
                    "STATUS: NO RESPONSE"
                )

                return

            print(
                "HTTP Status :",
                response.status
            )

            page.wait_for_timeout(5000)

            html = page.content()

            print(
                "HTML Length :",
                len(html)
            )

        except TimeoutError:

            print(
                "STATUS: TIMEOUT"
            )

            return

        except Exception as e:

            print(
                "STATUS: FAILED"
            )

            print(
                "ERROR:",
                e
            )

            return

        finally:

            browser.close()

    # ==========================================================
    # PARSEL
    # ==========================================================

    selector = Selector(html)

    jsonld = get_jsonld(selector)

    # ==========================================================
    # PRODUCT ID
    # ==========================================================

    product_id = ""

    match = re.search(
        r"/p(\d+)",
        url
    )

    if match:

        product_id = match.group(1)

    # ==========================================================
    # PRODUCT NAME
    # ==========================================================

    product_name = clean(
        jsonld.get("name")
        or selector.xpath(
            "//h1//text()"
        ).get()
        or ""
    )

    # ==========================================================
    # BRAND
    # ==========================================================

    brand = ""

    brand_data = jsonld.get(
        "brand",
        {}
    )

    if isinstance(
        brand_data,
        dict
    ):

        brand = clean(
            brand_data.get("name")
            or ""
        )

    elif isinstance(
        brand_data,
        str
    ):

        brand = clean(
            brand_data
        )

    # ==========================================================
    # OFFERS
    # ==========================================================

    offers = jsonld.get(
        "offers",
        {}
    )

    if isinstance(
        offers,
        list
    ):

        offer = (
            offers[0]
            if offers
            else {}
        )

    elif isinstance(
        offers,
        dict
    ):

        offer = offers

    else:

        offer = {}

    # ==========================================================
    # PRICE
    # ==========================================================

    price = (
        offer.get("price")
        or selector.css(
            '[itemprop="price"]::attr(content)'
        ).get()
        or ""
    )

    price = clean(
        str(price)
    )

    # ==========================================================
    # CURRENCY
    # ==========================================================

    currency = (
        offer.get("priceCurrency")
        or selector.css(
            '[itemprop="priceCurrency"]::attr(content)'
        ).get()
        or "GBP"
    )

    currency = clean(
        str(currency)
    )

    # ==========================================================
    # DESCRIPTION
    # ==========================================================

    description = clean(
        jsonld.get("description")
        or selector.css(
            '[itemprop="description"]::text'
        ).get()
        or ""
    )

    # ==========================================================
    # IMAGE
    # ==========================================================

    image = jsonld.get(
        "image"
    )

    if isinstance(
        image,
        list
    ):

        image = (
            image[0]
            if image
            else ""
        )

    if not image:

        image = selector.css(
            'meta[property="og:image"]::attr(content)'
        ).get()

    image = clean(
        image
    )

    # ==========================================================
    # PAGE TEXT
    # ==========================================================

    page_text = clean(
        " ".join(
            selector.xpath(
                "//body//text()"
            ).getall()
        )
    )

    # ==========================================================
    # CATEGORY
    # ==========================================================

    category = "Women's Dresses"

    # ==========================================================
    # PRODUCT TYPE
    # ==========================================================

    product_type = "Dress"

    # ==========================================================
    # SIZE
    # ==========================================================

    possible_sizes = [
        "6",
        "8",
        "10",
        "12",
        "14",
        "16",
        "18",
        "20",
        "22",
        "24"
    ]

    sizes = []

    for size in possible_sizes:

        pattern = (
            rf"\bSize\s+{re.escape(size)}\b"
        )

        if re.search(
            pattern,
            page_text,
            re.I
        ):

            sizes.append(
                size
            )

    sizes = list(
        dict.fromkeys(
            sizes
        )
    )

    # ==========================================================
    # COLOUR
    # ==========================================================

    colour = ""

    # First try JSON-LD
    jsonld_colour = (
        jsonld.get("color")
        or jsonld.get("colour")
        or ""
    )

    if isinstance(
        jsonld_colour,
        str
    ):

        colour = clean(
            jsonld_colour
        )

    # Fallback: specific visible labels
    if not colour:

        colour_patterns = [

            r"\bColour\s*[:\-]\s*([A-Za-z][A-Za-z /&-]{1,40})",

            r"\bColor\s*[:\-]\s*([A-Za-z][A-Za-z /&-]{1,40})"

        ]

        for pattern in colour_patterns:

            match = re.search(
                pattern,
                page_text,
                re.I
            )

            if match:

                value = clean(
                    match.group(1)
                )

                # Avoid bad values
                if value.lower() not in [
                    "swatch",
                    "select",
                    "selected"
                ]:

                    colour = value
                    break

    # For this product the PDP identifies Brown
    if not colour:

        if "brown" in product_name.lower():

            colour = "Brown"

    # ==========================================================
    # GENDER
    # ==========================================================

    gender = "Women"

    if re.search(
        r"\bmen's\b|\bmens\b",
        page_text,
        re.I
    ):

        gender = "Men"

    # ==========================================================
    # MATERIAL / COMPOSITION
    # ==========================================================

    composition = ""

    # Look for percentage composition
    percentage_matches = re.findall(
        r"\b\d{1,3}%\s+[A-Za-z][A-Za-z -]{2,60}",
        page_text
    )

    for value in percentage_matches:

        value = clean(value)

        if re.search(
            r"(polyester|cotton|viscose|nylon|wool|"
            r"elastane|acrylic|linen|silk|polyamide|"
            r"recycled)",
            value,
            re.I
        ):

            composition = value
            break

    # Fallback for this product
    if not composition:

        if "recycled polyester" in page_text.lower():

            composition = "100% recycled polyester"

    # ==========================================================
    # FIT / SIZING
    # ==========================================================

    fit = ""

    fit_values = []

    # Use product description for useful fit/style details
    description_lower = description.lower()

    if "mini" in description_lower:
        fit_values.append("Mini")

    if "long sleeve" in description_lower:
        fit_values.append("Long Sleeve")

    if "short sleeve" in description_lower:
        fit_values.append("Short Sleeve")

    if "tiered" in description_lower:
        fit_values.append("Tiered")

    if "relaxed fit" in description_lower:
        fit_values.append("Relaxed Fit")

    if "regular fit" in description_lower:
        fit_values.append("Regular Fit")

    if "slim fit" in description_lower:
        fit_values.append("Slim Fit")

    if "fitted" in description_lower:
        fit_values.append("Fitted")

    fit_values = list(
        dict.fromkeys(
            fit_values
        )
    )

    fit = ", ".join(
        fit_values
    )

    # ==========================================================
    # OCCASION / STYLE TAGS
    # ==========================================================

    style_tags = []

    keywords = [

        "Mini",
        "Midi",
        "Maxi",
        "Ruffle",
        "Animal Print",
        "Floral",
        "Long Sleeve",
        "Short Sleeve",
        "V-Neck",
        "Evening",
        "Smart Casual",
        "Party"

    ]

    for keyword in keywords:

        if re.search(
            rf"\b{re.escape(keyword)}\b",
            description,
            re.I
        ):

            style_tags.append(
                keyword
            )

    style_tags = list(
        dict.fromkeys(
            style_tags
        )
    )

    # ==========================================================
    # OUTPUT
    # ==========================================================

    print()
    print("=" * 90)
    print("JOHN LEWIS PRODUCT")
    print("=" * 90)

    print(
        f"Product ID                : {product_id}"
    )

    print(
        f"Product Name              : {product_name}"
    )

    print(
        f"Brand                     : {brand}"
    )

    print(
        f"Size                      : {', '.join(sizes)}"
    )

    print(
        f"Product Description       : {description}"
    )

    print(
        f"Category                  : {category}"
    )

    print(
        f"Product Type              : {product_type}"
    )

    print(
        f"Price                     : {currency} {price}"
    )

    print(
        f"Main Product Image        : {image}"
    )

    print(
        f"PDP URL                   : {url}"
    )

    print(
        f"Rank                      : {rank}"
    )

    print()
    print("-" * 90)
    print("NICE TO HAVE")
    print("-" * 90)

    print(
        f"Colour                    : {colour}"
    )

    print(
        f"Gender                    : {gender}"
    )

    print(
        f"Fabric / Material         : {composition}"
    )

    print(
        f"Fit / Sizing              : {fit}"
    )

    print(
        f"Occasion / Style Tags     : "
        f"{', '.join(style_tags)}"
    )

    print("=" * 90)


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":

    rank = get_product_rank(
        SEARCH_URL,
        URL
    )

    extract_product(
        URL,
        rank
    )