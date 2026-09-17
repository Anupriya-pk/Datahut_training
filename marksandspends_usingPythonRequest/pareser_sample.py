

import json
import re
import time
import html as html_module

import requests

from items_sample import ProductItem

from settings_sample import (
    BASE_URL,
    REQUEST_DELAY,
    TIMEOUT,
    HEADERS,
    PRODUCT_URL_FILE,
)


session = requests.Session()
session.headers.update(HEADERS)


def clean_text(value):

    if value is None:
        return ""

    value = html_module.unescape(str(value))

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def load_product_urls():

    urls = []

    try:

        with open(
            PRODUCT_URL_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            for line in file:

                url = line.strip()

                if url:
                    urls.append(url)

    except FileNotFoundError:

        print(
            f"{PRODUCT_URL_FILE} not found."
        )

    return urls


def extract_json_ld(html):

    """
    Extract JSON-LD blocks from product page.
    """

    products = []

    pattern = re.compile(
        r'<script[^>]+type=["\']application/ld\+json'
        r'["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL
    )

    matches = pattern.findall(html)

    for block in matches:

        block = block.strip()

        try:

            data = json.loads(block)

        except json.JSONDecodeError:

            continue

        if isinstance(data, dict):

            products.append(data)

        elif isinstance(data, list):

            products.extend(data)

    return products


def find_product_json(json_objects):

    for data in json_objects:

        if not isinstance(data, dict):
            continue

        data_type = data.get("@type", "")

        if isinstance(data_type, list):

            types = data_type

        else:

            types = [data_type]

        if "Product" in types:

            return data

    return {}


def extract_meta_content(html, property_name=None, name=None):

    if property_name:

        pattern = (
            r'<meta[^>]+'
            r'property=["\']'
            + re.escape(property_name)
            + r'["\'][^>]+'
            r'content=["\']([^"\']*)["\']'
        )

    else:

        pattern = (
            r'<meta[^>]+'
            r'name=["\']'
            + re.escape(name)
            + r'["\'][^>]+'
            r'content=["\']([^"\']*)["\']'
        )

    match = re.search(
        pattern,
        html,
        re.IGNORECASE
    )

    if match:
        return clean_text(match.group(1))

    return ""


def extract_product_code(html):

    patterns = [

        r'Product\s*code[^A-Za-z0-9]{0,50}'
        r'([A-Z0-9][A-Z0-9\-\/]{4,20})',

        r'"productCode"\s*:\s*"([^"]+)"',

        r'"productId"\s*:\s*"([^"]+)"',

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE
        )

        if match:
            return clean_text(match.group(1))

    return ""


def extract_colour(html):

    patterns = [

        r'"color"\s*:\s*"([^"]+)"',

        r'"colour"\s*:\s*"([^"]+)"',

        r'Colour\s*Colour\s*([^<]{2,50})',

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE
        )

        if match:

            value = clean_text(match.group(1))

            if value:
                return value

    return ""


def extract_price(html, product_json):

    offers = product_json.get("offers", {})

    if isinstance(offers, list) and offers:
        offers = offers[0]

    if isinstance(offers, dict):

        price = offers.get("price")

        currency = offers.get(
            "priceCurrency",
            ""
        )

        if price:

            return (
                clean_text(price),
                clean_text(currency)
            )


    patterns = [

        r'"price"\s*:\s*"([^"]+)"',

        r'"price"\s*:\s*([0-9]+(?:\.[0-9]+)?)',

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE
        )

        if match:

            return (
                clean_text(match.group(1)),
                "GBP"
            )

    return "", ""


def extract_description(html, product_json):

    description = product_json.get(
        "description",
        ""
    )

    if description:

        return clean_text(description)

    
    patterns = [

        r'About this style.*?'
        r'(?:Details & care|Delivery)',
        
        r'PRODUCT DESCRIPTION.*?'
        r'(?:DETAILS & CARE|DELIVERY)',

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE | re.DOTALL
        )

        if match:

            value = clean_text(match.group(0))

            value = re.sub(
                r'About this style',
                '',
                value,
                flags=re.IGNORECASE
            )

            value = re.sub(
                r'PRODUCT DESCRIPTION',
                '',
                value,
                flags=re.IGNORECASE
            )

            return value.strip()

    return ""


def extract_composition(html):

    patterns = [

        r'Composition\s*</[^>]+>\s*'
        r'(?:<[^>]+>\s*)*'
        r'([^<]{3,200})',

        r'"composition"\s*:\s*"([^"]+)"',

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE | re.DOTALL
        )

        if match:

            value = clean_text(match.group(1))

            if value:
                return value

    return ""


def extract_fit(html):

    patterns = [

        r'Fit and style.*?'
        r'((?:Regular fit|Relaxed fit|Slim fit|'
        r'Oversized fit|Loose fit|Fitted fit))',

        r'"fit"\s*:\s*"([^"]+)"',

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE | re.DOTALL
        )

        if match:

            return clean_text(
                match.group(1)
            )

    return ""




def extract_image(html, product_json):

    image = product_json.get(
        "image",
        ""
    )

    if isinstance(image, list):

        if image:
            return clean_text(image[0])

    if isinstance(image, str) and image:
        return clean_text(image)

    patterns = [

        r'"image"\s*:\s*"([^"]+)"',

        r'<meta[^>]+'
        r'property=["\']og:image["\']'
        r'[^>]+content=["\']([^"\']+)["\']',

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE
        )

        if match:

            return clean_text(
                match.group(1)
            )

    return ""


def extract_brand(product_json, html):

    brand = product_json.get(
        "brand",
        ""
    )

    if isinstance(brand, dict):

        brand = brand.get(
            "name",
            ""
        )

    if brand:
        return clean_text(brand)

    
    if re.search(
        r'M&S Collection',
        html,
        re.IGNORECASE
    ):
        return "M&S"

    return ""


def parse_product(url):

    print("-" * 70)
    print("PRODUCT URL:")
    print(url)

    try:

        response = session.get(
            url,
            timeout=TIMEOUT
        )

    except requests.RequestException as error:

        print("Request failed:", error)
        return None

    print("Status:", response.status_code)

    if response.status_code != 200:

        print(
            "Failed product page"
        )

        return None

    html = response.text

    json_objects = extract_json_ld(html)

    product_json = find_product_json(
        json_objects
    )

    item = ProductItem()

    

    name = product_json.get(
        "name",
        ""
    )

    if not name:

        name = extract_meta_content(
            html,
            property_name="og:title"
        )

    item.product_name = clean_text(name)

    

    product_id = product_json.get(
        "sku",
        ""
    )

    item.product_id = clean_text(
        product_id
    )

  

    item.product_code = (
        extract_product_code(html)
    )

    

    item.brand = extract_brand(
        product_json,
        html
    )


    price, currency = extract_price(
        html,
        product_json
    )

    item.price = price
    item.currency = currency

    

    item.colour = extract_colour(
        html
    )

  

    

    item.description = (
        extract_description(
            html,
            product_json
        )
    )


    item.composition = (
        extract_composition(html)
    )

    

    item.fit = extract_fit(
        html
    )

    

   

    item.image = extract_image(
        html,
        product_json
    )

   

    item.product_url = url

    return item


def parse_all_products():

    urls = load_product_urls()

    print()
    print(
        "TOTAL PRODUCT URLS:",
        len(urls)
    )

    products = []

    for index, url in enumerate(
        urls,
        start=1
    ):

        print()
        print(
            f"PROCESSING PRODUCT "
            f"{index}/{len(urls)}"
        )

        item = parse_product(url)

        if item:

            products.append(
                item.to_dict()
            )

        time.sleep(
            REQUEST_DELAY
        )

    return products


def save_json(products):

    with open(
        "parsed_products.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            products,
            file,
            indent=4,
            ensure_ascii=False
        )


def main():

    products = parse_all_products()

    save_json(products)

    print()
    print("=" * 70)
    print("PARSING COMPLETED")
    print("=" * 70)
    print(
        "PRODUCTS PARSED:",
        len(products)
    )
    print(
        "SAVED TO: parsed_products.json"
    )


if __name__ == "__main__":
    main()