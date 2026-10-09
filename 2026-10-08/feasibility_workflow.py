#  crawler

from playwright.sync_api import sync_playwright
from urllib.parse import urlencode
import csv

SEARCH_KEYWORD = "Apple AirTag (2nd generation)"
TARGET_URLS = 50
MAX_PAGES = 10
PROFILE_DIR = "amazon_profile"
OUT_CSV = "amazon_airtag_product_urls.csv"
RESULT_SEL = '[data-component-type="s-search-result"]'


def is_login_or_captcha(page):
    return ("/ap/signin" in page.url or "captcha" in page.url.lower()
            or page.locator("form[action*='validateCaptcha']").count() > 0)


with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(PROFILE_DIR, headless=False, locale="en-GB")
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # skip images / fonts / media so pages load faster
    ctx.route(
        "**/*",
        lambda route: route.abort()
        if route.request.resource_type in ("image", "media", "font")
        else route.continue_(),
    )

    products = {}   # asin -> url (keeps order, no duplicates)

    for page_no in range(1, MAX_PAGES + 1):
        if len(products) >= TARGET_URLS:
            break

        url = "https://www.amazon.de/s?" + urlencode({"k": SEARCH_KEYWORD, "page": page_no})
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        if is_login_or_captcha(page):
            input("\nSign-in / CAPTCHA shown. Handle it in the browser, "
                  "wait until results are visible, then press ENTER here...")

        try:
            page.wait_for_selector(RESULT_SEL, timeout=15000)
        except Exception:
            print(f"Page {page_no}: no result cards found, stopping.")
            break

        # scroll so lazy-loaded results appear
        for _ in range(4):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(300)

        asins = page.eval_on_selector_all(
            f"{RESULT_SEL}[data-asin]",
            "els => els.map(e => e.getAttribute('data-asin'))",
        )

        before = len(products)
        for asin in asins:
            if asin and len(asin) == 10 and len(products) < TARGET_URLS:
                products.setdefault(asin, f"https://www.amazon.de/dp/{asin}")

        print(f"Search page {page_no}: +{len(products) - before} new "
              f"(total {len(products)}/{TARGET_URLS})")

        if len(products) == before:
            print("No new products on this page, stopping.")
            break

    urls = list(products.values())

    print("\n========== PRODUCT URLS ==========")
    for i, u in enumerate(urls, 1):
        print(f"{i}. {u}")

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["url", "product_sku"])
        for u in urls:
            w.writerow([u, u.rsplit("/", 1)[-1]])

    print(f"\nTotal URLs: {len(urls)}  ->  saved to {OUT_CSV}")
    ctx.close()


# *****************************************************************

#  review parser
from playwright.sync_api import sync_playwright
from parsel import Selector
from datetime import datetime
from urllib.parse import urlencode
import re
import json
import csv
import random

ASIN = "B0GJTMMWRS"
PRODUCT_URL = f"https://www.amazon.de/-/en/dp/{ASIN}/"
BASE_REVIEWS = f"https://www.amazon.de/product-reviews/{ASIN}/"
TARGET = 200
MAX_PAGES = 2                   # page 2+ rarely gives new reviews, so keep it small
PROFILE_DIR = "amazon_profile"  # login is saved here
REVIEW_SEL = '[data-hook="review"]'

STAR_FILTERS = [None, "five_star", "four_star", "three_star", "two_star", "one_star"]
SORTS = ["recent", "helpful"]
FORMATS = ["current_format", "all_formats"]      # all_formats includes other pack sizes
REVIEWERS = ["all_reviews", "avp_only_reviews"]  # avp = verified purchase only

# CHANGE 1: keyword searches. Each keyword shows a different slice of reviews.
# Add more words here if you need more reviews.
KEYWORDS = [
    # English
    "battery", "sound", "speaker", "iPhone", "keys", "luggage", "bag", "wallet",
    "bike", "car", "dog", "cat", "kids", "price", "delivery", "setup", "range",
    "precision", "location", "tracking", "lost", "holder", "case", "keychain",
    "design", "volume", "accuracy", "gift", "recommend", "works", "great",
    "good", "problem", "Apple", "Find My", "compact", "size", "quality",
    "worth", "alarm", "notification", "Android",
    # German
    "Schlüssel", "Akku", "Lautsprecher", "Preis", "Lieferung", "Koffer",
    "Fahrrad", "Hund", "Katze", "Rucksack", "Tasche", "Ortung", "Reichweite",
    "Einrichtung", "Qualität", "Geschenk", "empfehlen", "super", "gut",
    "Anhänger", "Hülle", "Lautstärke", "Genauigkeit", "Verbindung",
]


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def clean(text):
    return " ".join(text.split()) if text else ""


def extract_rating(text):
    if not text:
        return ""
    m = re.search(r"(\d+(?:\.\d+)?)\s*out of\s*5", text)
    return m.group(1) if m else ""


def get_star_distribution(rating):
    d = {f"{i}_star": 0 for i in range(1, 6)}
    try:
        key = str(int(float(rating)))
    except (ValueError, TypeError):
        return d
    if key in ["1", "2", "3", "4", "5"]:
        d[f"{key}_star"] = 1
    return d


def normalize_id(rid):
    """Make IDs identical across product page and reviews page."""
    return re.sub(r"^customer_review(_foreign)?[-_]", "", rid or "")


def parse_date(raw):
    """'Reviewed in Germany on 5 October 2026' -> ('Germany', '2026-10-05')"""
    country, iso = "", ""
    m = re.search(r"Reviewed in (?:the )?(.+?) on (.+)$", raw or "")
    if m:
        country = m.group(1).strip()
        date_str = m.group(2).strip()
    else:
        date_str = raw or ""
    for fmt in ("%d %B %Y", "%B %d, %Y", "%d. %B %Y"):
        try:
            iso = datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            break
        except ValueError:
            continue
    return country, iso


# ---------------------------------------------------------
# PARSING
# ---------------------------------------------------------

def parse_reviews(html, product_name, avg_rating, collected):
    """Add NEW reviews to `collected`. Returns number of new reviews."""
    sel = Selector(text=html)
    new = 0
    for review in sel.css(REVIEW_SEL):
        rid = normalize_id(review.attrib.get("id", ""))
        if not rid or rid in collected:
            continue

        rating_text = clean(review.css('[data-hook="review-star-rating"] .a-icon-alt::text').get()) \
            or clean(review.css('[data-hook="cmps-review-star-rating"] .a-icon-alt::text').get())
        rating = extract_rating(rating_text)

        # REVIEW TEXT
        text_parts = review.css('[data-hook="reviewRichContentContainer"] ::text').getall()
        if not any(clean(t) for t in text_parts):
            text_parts = review.css('[data-hook="review-body"] ::text').getall()
        if not any(clean(t) for t in text_parts):
            text_parts = review.css('[data-hook="reviewText"] ::text').getall()

        # REVIEW DATE
        date_raw = clean(" ".join(review.css('[data-hook="review-date"] ::text').getall()))
        country, date_iso = parse_date(date_raw)

        collected[rid] = {
            "product_name": product_name,
            "product_average_rating": avg_rating,
            "review_id": rid,
            "rating": rating,
            "star_distribution": get_star_distribution(rating),
            "review_title": clean(" ".join(review.css('[data-hook="reviewTitle"] ::text').getall())),
            "review_text": clean(" ".join(text_parts)),
            "review_date": date_raw,
            "review_date_clean": date_iso,
            "review_country": country,
            "verified_purchase": bool(review.css('[data-hook="avp-badge"]')),
        }
        new += 1
    return new


# ---------------------------------------------------------
# NAVIGATION
# ---------------------------------------------------------

def is_login_page(page):
    return "/ap/signin" in page.url or "signin" in page.url


def is_captcha(page):
    return "captcha" in page.url.lower() or page.locator("form[action*='validateCaptcha']").count() > 0


def open_url(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(random.randint(2000, 3500))

    if is_login_page(page):
        input("\nLogin needed. Log in in the browser window, then press ENTER here...")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

    if is_captcha(page):
        input("\nCAPTCHA shown. Solve it in the browser window, then press ENTER here...")
        page.wait_for_timeout(2000)


# CHANGE 2: URL now supports format, reviewer type and keyword
def build_url(page_no, sort, star, fmt, reviewer, keyword):
    params = {
        "reviewerType": reviewer,
        "formatType": fmt,
        "sortBy": sort,
        "pageNumber": page_no,
    }
    if star:
        params["filterByStar"] = star
    if keyword:
        params["filterByKeyword"] = keyword
    return f"{BASE_REVIEWS}?{urlencode(params)}"


# CHANGE 3: many filter combinations instead of only sort x star
def filter_combinations():
    # Pass 1: format x reviewer type x sort x star (no keyword)
    for fmt in FORMATS:
        for reviewer in REVIEWERS:
            for sort in SORTS:
                for star in STAR_FILTERS:
                    yield sort, star, fmt, reviewer, None
    # Pass 2: every keyword x every star x sort
    for keyword in KEYWORDS:
        for star in STAR_FILTERS:
            for sort in SORTS:
                yield sort, star, "all_formats", "all_reviews", keyword


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(PROFILE_DIR, headless=False, locale="en-GB")
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # 1) Product page: name + average rating + first reviews
    page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)

    try:
        product_name = clean(page.locator("#productTitle").inner_text(timeout=10000))
    except Exception:
        product_name = ""

    avg_rating = ""
    for css in ["#acrPopover .a-icon-alt", '[data-hook="rating-out-of-text"]']:
        try:
            r = extract_rating(clean(page.locator(css).first.inner_text(timeout=2000)))
            if r:
                avg_rating = r
                break
        except Exception:
            continue

    collected = {}
    parse_reviews(page.content(), product_name, avg_rating, collected)

    # 2) Go through all filter combinations until we have 200 reviews
    for sort, star, fmt, reviewer, keyword in filter_combinations():
        if len(collected) >= TARGET:
            break

        for page_no in range(1, MAX_PAGES + 1):
            open_url(page, build_url(page_no, sort, star, fmt, reviewer, keyword))

            if page.locator(REVIEW_SEL).count() == 0:
                break

            new = parse_reviews(page.content(), product_name, avg_rating, collected)
            print(f"\rCollected: {len(collected)}", end="", flush=True)

            if len(collected) >= TARGET or new == 0:
                break

    print()  # finish the progress line

    # 3) Build final list and number the reviews
    reviews = list(collected.values())[:TARGET]
    for i, r in enumerate(reviews, 1):
        r["review_number"] = i

    # 4) Print each review with all fields
    for r in reviews:
        print(f"\n{'#' * 80}")
        print(f"REVIEW {r['review_number']}")
        print('#' * 80)
        print(f"Product name         : {r['product_name']}")
        print(f"Product avg rating   : {r['product_average_rating'] or 'Not found'}")
        print(f"Review ID            : {r['review_id'] or 'Not available'}")
        print(f"Review rating        : {r['rating'] or 'Not found'}")
        print(f"Star distribution    : {json.dumps(r['star_distribution'])}")
        print(f"Review title         : {r['review_title'] or 'Not available'}")
        print(f"Review date (raw)    : {r['review_date'] or 'Not found'}")
        print(f"Review date (clean)  : {r['review_date_clean'] or 'Not found'}")
        print(f"Review country       : {r['review_country'] or 'Not found'}")
        print(f"Verified purchase    : {r['verified_purchase']}")
        print(f"Review text          : {r['review_text'] or 'Not found'}")

    # 5) Save JSON
    with open("amazon_airtag_reviews.json", "w", encoding="utf-8") as f:
        json.dump({
            "product_name": product_name,
            "product_url": PRODUCT_URL,
            "product_average_rating": avg_rating,
            "number_of_reviews": len(reviews),
            "reviews": reviews,
        }, f, ensure_ascii=False, indent=4)

    # 6) Save CSV (one row per review)
    with open("amazon_airtag_reviews.csv", "w", newline="", encoding="utf-8-sig") as f:
        fields = ["review_number", "review_id", "rating", "review_title",
                  "review_text", "review_date", "review_date_clean",
                  "review_country", "verified_purchase"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(reviews)

    ctx.close()







