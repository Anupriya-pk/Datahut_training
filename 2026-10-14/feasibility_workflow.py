# CRAWLER
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from urllib.parse import urlparse
import csv
import time

CATEGORY_NAME = "Fruits & Vegetables"
START_URL = "https://www.migros.ch/en/category/fruits-vegetables"
OUTPUT_FILE = "migros_product_urls.csv"
BASE_DOMAIN = "www.migros.ch"
MAX_SCROLL_ROUNDS = 30
WAIT_AFTER_LOAD = 4000
SCROLL_WAIT = 2000

def is_product_url(url):
    parsed = urlparse(url)
    return parsed.netloc == BASE_DOMAIN and parsed.path.startswith("/en/product/")

def is_category_url(url):
    parsed = urlparse(url)
    return parsed.netloc == BASE_DOMAIN and parsed.path.rstrip("/") == "/en/category/fruits-vegetables"

def normalize_product_url(url):
    parsed = urlparse(url)
    return f"https://{parsed.netloc}{parsed.path}" if is_product_url(url) else None

def collect_products_from_listing(page):
    product_urls, last_count, stable_rounds = set(), 0, 0
    for _ in range(MAX_SCROLL_ROUNDS):
        links = page.locator('a[href*="/en/product/"]').evaluate_all("elements => elements.map(element => element.href)")
        product_urls.update(clean for url in links if (clean := normalize_product_url(url)))
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(SCROLL_WAIT)
        stable_rounds = stable_rounds + 1 if len(product_urls) == last_count else 0
        last_count = len(product_urls)
        if stable_rounds >= 2:
            break
    return product_urls

def get_next_page(page):
    links = page.locator("a[href]").evaluate_all("""
        elements => elements.map(element => ({
            href: element.href,
            text: ((element.innerText || element.textContent || "")).trim(),
            rel: element.getAttribute("rel") || "",
            ariaLabel: element.getAttribute("aria-label") || ""
        }))
    """)
    for link in links:
        href = link["href"]
        if not is_category_url(href):
            continue
        text = (link["text"] + " " + link["ariaLabel"]).lower()
        if (link["rel"].lower() == "next" or any(word in text for word in ("next", "weiter", "nächste"))) and href != page.url:
            return href
    return None

def crawl_category(page):
    all_product_urls, visited_pages = set(), set()
    current_page_url = START_URL
    while current_page_url and current_page_url not in visited_pages:
        visited_pages.add(current_page_url)
        try:
            response = page.goto(current_page_url, wait_until="domcontentloaded", timeout=60000)
        except PlaywrightTimeoutError:
            break
        if response is None or response.status >= 400:
            break
        page.wait_for_timeout(WAIT_AFTER_LOAD)
        all_product_urls.update(collect_products_from_listing(page))
        next_page_url = get_next_page(page)
        if not next_page_url or next_page_url in visited_pages:
            break
        current_page_url = next_page_url
        time.sleep(1)
    return all_product_urls

def save_csv(product_urls):
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["product_url"])
        writer.writerows([url] for url in sorted(product_urls))

def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            product_urls = crawl_category(page)
        finally:
            browser.close()
    save_csv(product_urls)
    print("Category:", CATEGORY_NAME)
    print("Total number of products:", len(product_urls))
    print("CSV file saved:", OUTPUT_FILE)

if __name__ == "__main__":
    main()

#  ##########################################################################################
# PARSER
import csv
import json
import re
from datetime import date
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from migros_fields import fields as FIELDS

# CONFIGURATION
PRODUCT_URL = "https://www.migros.ch/en/product/130858800000"
PRODUCT_ID = "130858800000"
OUTPUT_CSV = "migros_product_130858800000.csv"
TIMEOUT = 60000
HEADLESS = False

# XPATHS
XPATHS = {
    "product_name": "(//h1[starts-with(@data-testid, 'product-detail-') and contains(@data-testid, '-title')])[1]",
    "brand": "(//img[@data-testid='product-detail-brand-label'])[1]",
    "quantity": "(//*[starts-with(@data-testid, 'product-detail-') and contains(@data-testid, '-weight')])[1]",
    "regular_price": "(//span[@data-testid='default-actual-price'])[1]",
    "ingredients": "(//dd[contains(@data-testid, '-ingredients')])[1]",
    "rating_summary": "(//*[contains(@data-testid, '-rating')])[1]",
    "distributor_address": "(//dd[contains(@data-testid, '-distribution')])[1]",
    "article_number": "(//dd[contains(@data-testid, '-product_id')])[1]",
    "description": "(//meta[@name='description'])[1]",
    "pdp_url": "(//meta[@property='og:url'])[1]",
    "image_url": "(//meta[@property='og:image'])[1]",
    "nutritional_rows": "//mo-product-detail-nutrients-information//table[contains(@class, 'nutrients-table')]//tr[td]",
    "json_ld": "//script[@type='application/ld+json']",
}

# CAPTURE PRODUCT JSON
captured_product_json = {}

def capture_response(response):
    if response.status != 200 or PRODUCT_ID not in response.url:
        return
    if "/product-display/public/v1/products/mgb/" not in response.url:
        return
    try:
        data = response.json()
        if isinstance(data, dict) and str(data.get("migrosId", "")) == PRODUCT_ID:
            captured_product_json.clear()
            captured_product_json.update(data)
    except Exception:
        pass

# XPATH HELPERS
def xpath_text(page, expression):
    try:
        locator = page.locator("xpath=" + expression).first
        if locator.count():
            value = locator.inner_text(timeout=3000)
            if value:
                return " ".join(value.split()).strip()
    except Exception:
        pass
    return ""

def xpath_attribute(page, expression, attribute):
    try:
        locator = page.locator("xpath=" + expression).first
        if locator.count():
            value = locator.get_attribute(attribute, timeout=3000)
            if value:
                return value.strip()
    except Exception:
        pass
    return ""

def xpath_rows(page, expression):
    try:
        return page.locator("xpath=" + expression).evaluate_all("""
            rows => rows.map(row =>
                Array.from(row.querySelectorAll("th, td")).map(cell => cell.innerText.trim())
            ).filter(cells => cells.some(value => value !== ""))
        """)
    except Exception:
        return []

# JSON HELPERS
def get_path(data, path):
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current

def first_value(data, paths):
    for path in paths:
        value = get_path(data, path)
        if value is not None and value != "":
            return value
    return None

def json_text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return str(value).strip()

def price_text(value):
    if value is None:
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return json_text(value)

# JSON-LD FALLBACK
def read_json_ld(page):
    product_schema, breadcrumb_schema = {}, []
    try:
        scripts = page.locator("xpath=" + XPATHS["json_ld"]).all_text_contents()
    except Exception:
        return product_schema, breadcrumb_schema

    for script_text in scripts:
        try:
            payload = json.loads(script_text)
        except (ValueError, TypeError):
            continue

        for obj in (payload if isinstance(payload, list) else [payload]):
            if not isinstance(obj, dict):
                continue
            obj_type = obj.get("@type")
            if obj_type == "Product":
                if PRODUCT_ID in obj.get("url", ""):
                    product_schema = obj
            elif obj_type == "BreadcrumbList":
                names = [str(entry["name"]).strip() for entry in obj.get("itemListElement", []) if isinstance(entry, dict) and entry.get("name")]
                if names:
                    breadcrumb_schema = names

    return product_schema, breadcrumb_schema

# FIELD HELPERS
def parse_quantity(value):
    if not value:
        return "", ""
    match = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*([A-Za-zµμ]+)\s*", str(value))
    if not match:
        return "", ""
    return match.group(1).replace(",", "."), match.group(2)

def format_distributor(product, xpath_fallback):
    other = get_path(product, "productInformation.otherInformation") or {}
    parts = [str(value).strip() for value in (other.get("distributorName", ""), other.get("distributorStreetAndNumber", "")) if value]
    return ", ".join(parts) if parts else xpath_fallback

def get_breadcrumb_names(product, jsonld_breadcrumb):
    if jsonld_breadcrumb:
        return jsonld_breadcrumb
    breadcrumb = product.get("breadcrumb", [])
    names = [str(item["name"]).strip() for item in breadcrumb if isinstance(item, dict) and item.get("name")] if isinstance(breadcrumb, list) else []
    product_name = product.get("name", "")
    if product_name and (not names or product_name not in names[-1]):
        names.append(product_name)
    return names

def nutrition_data(product, dom_rows):
    table = first_value(product, ["productInformation.nutrientsInformation.nutrientsTableV2", "productInformation.nutrientsInformation.nutrientsTable"])
    if isinstance(table, dict):
        return table
    if dom_rows:
        return {"rows": [{"label": cells[0], "values": cells[1:]} for cells in dom_rows if cells]}
    return None

def nutrition_summary(table):
    if not isinstance(table, dict):
        return ""
    output = []
    for row in table.get("rows", []):
        if not isinstance(row, dict):
            continue
        label, values = row.get("label", ""), row.get("values", [])
        if label and values:
            output.append(f"{label}: {' / '.join(str(v) for v in values if v)}")
    return "; ".join(output)

def get_image_url(page, product):
    image_url = xpath_attribute(page, XPATHS["image_url"], "content")
    if image_url and "{stack}" not in image_url:
        return image_url

    image_url = xpath_attribute(page, "(//img[contains(@class, 'no-fade') and contains(@class, 'is-imageloaded')])[1]", "src")
    if image_url and "{stack}" not in image_url:
        return image_url

    images = product.get("images", [])
    if isinstance(images, list):
        for image in images:
            if not isinstance(image, dict):
                continue
            candidate = image.get("url", "")
            if isinstance(candidate, str) and candidate.startswith("https://") and "{stack}" not in candidate:
                return candidate
    return ""

# EXTRACT THE 27 REQUIRED FIELDS
def extract_record(page, product, schema_product, breadcrumb_schema):
    row = {field: "" for field in FIELDS}

    article_number = xpath_text(page, XPATHS["article_number"])
    unique_id = product.get("migrosId") or article_number or PRODUCT_ID
    row["unique_id"] = str(unique_id)
    row["competitor_name"] = "Migros"
    row["extraction_date"] = date.today().isoformat()
    row["pdp_url"] = product.get("productUrls") or xpath_attribute(page, XPATHS["pdp_url"], "content") or PRODUCT_URL

    product_name = product.get("name") or schema_product.get("name") or xpath_text(page, XPATHS["product_name"])
    row["product_name"] = json_text(product_name)

    brand = product.get("brand") or get_path(product, "productInformation.mainInformation.brand.name") or get_path(schema_product, "brand.name") or xpath_attribute(page, XPATHS["brand"], "alt")
    row["brand"] = json_text(brand)

    offer = product.get("offer", {})
    if not isinstance(offer, dict):
        offer = {}

    quantity = offer.get("quantity") or xpath_text(page, XPATHS["quantity"])
    row["grammage_quantity"], row["grammage_unit"] = parse_quantity(quantity)
    if quantity:
        row["site_shown_uom"] = str(quantity).strip()
        row["netcontent"] = str(quantity).strip()

    breadcrumb_names = get_breadcrumb_names(product, breadcrumb_schema)
    if breadcrumb_names:
        row["breadcrumb"] = " > ".join(breadcrumb_names)
        for index, name in enumerate(breadcrumb_names[:3], start=1):
            row[f"producthierarchy_level{index}"] = name

    price = offer.get("price", {})
    if not isinstance(price, dict):
        price = {}

    displayed_price = xpath_text(page, XPATHS["regular_price"])
    advertised_value = price.get("advertisedValue")
    effective_value = price.get("effectiveValue")

    if advertised_value is not None and effective_value is not None and advertised_value == effective_value:
        row["regular_price"] = price_text(advertised_value)
    elif displayed_price and re.fullmatch(r"\s*\d+(?:[.,]\d{1,2})?\s*", displayed_price):
        row["regular_price"] = price_text(displayed_price.replace(",", "."))

    row["product_description"] = product.get("description") or schema_product.get("description") or xpath_attribute(page, XPATHS["description"], "content")
    row["ingredients"] = get_path(product, "productInformation.mainInformation.ingredients") or xpath_text(page, XPATHS["ingredients"])
    row["distributor_address"] = format_distributor(product, xpath_text(page, XPATHS["distributor_address"]))

    table = nutrition_data(product, xpath_rows(page, XPATHS["nutritional_rows"]))
    if table:
        row["nutritional_information"] = json.dumps(table, ensure_ascii=False, separators=(",", ":"))
        row["nutritions"] = nutrition_summary(table)

    gtins = product.get("gtins", [])
    if isinstance(gtins, list):
        row["barcode"] = "; ".join(str(gtin) for gtin in gtins if gtin)
    elif gtins:
        row["barcode"] = str(gtins)

    rating_data = get_path(product, "productInformation.mainInformation.rating") or {}
    if isinstance(rating_data, dict):
        stars = rating_data.get("nbStars")
        if stars is not None:
            row["rating"] = str(stars)
        review_count = rating_data.get("nbReviews")
        if review_count is not None:
            row["review"] = f"{review_count} ratings on Migipedia"

    if not row["review"]:
        row["review"] = xpath_text(page, XPATHS["rating_summary"])

    if not row["rating"]:
        aggregate_rating = schema_product.get("aggregateRating", {})
        if isinstance(aggregate_rating, dict):
            row["rating"] = json_text(aggregate_rating.get("ratingValue"))
            count = aggregate_rating.get("reviewCount")
            if count is not None and not row["review"]:
                row["review"] = f"{count} ratings"

    online_id = product.get("migrosOnlineId")
    if online_id is not None:
        row["competitor_product_key"] = str(online_id)
    if unique_id:
        row["product_unique_key"] = f"{unique_id}P"

    image_url = get_image_url(page, product)
    if image_url:
        row["image_url_1"] = image_url

    return row

# MAIN
def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=HEADLESS)
        page = browser.new_page(locale="en-CH", viewport={"width": 1440, "height": 1000})
        page.on("response", capture_response)

        try:
            response = page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
            if response is None:
                raise RuntimeError("No response received for product page.")
            if response.status >= 400:
                raise RuntimeError(f"Product page returned HTTP {response.status}.")

            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeoutError:
                pass

            page.wait_for_timeout(2000)
            product_data = captured_product_json.copy()
            schema_product, breadcrumb_schema = read_json_ld(page)
            record = extract_record(page, product_data, schema_product, breadcrumb_schema)
        finally:
            browser.close()

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, delimiter="|", extrasaction="ignore")
        writer.writeheader()
        writer.writerow(record)

    populated = sum(1 for field in FIELDS if record.get(field) not in (None, ""))
    print("Product URL:", PRODUCT_URL)
    print("Fields populated:", populated, "of", len(FIELDS))
    print("CSV file saved:", OUTPUT_CSV)

if __name__ == "__main__":
    main()




























