

BASE_URL = "https://www.marksandspencer.com"

LISTING_URL = "https://www.marksandspencer.com/l/women/dresses"

# Only pages 1 to 10
MAX_PAGES = 10

REQUEST_DELAY = 1.5

TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Connection": "keep-alive",
}

PRODUCT_URL_FILE = "product_urls.csv"

OUTPUT_FILE = "output.csv"