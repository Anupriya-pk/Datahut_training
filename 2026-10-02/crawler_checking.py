from playwright.sync_api import sync_playwright, TimeoutError
import re
import time


BASE_URL = "https://www.johnlewis.com/search?search-term={}"


KEYWORDS = [
    "mini dress",
    "midi dress",
    "maxi dress",
    "summer dress",
    "knitted dress",

    "wide leg jeans",
    "straight jeans",
    "skinny jeans",
    "flared jeans",
    "high waist jeans",

    "fine knit jumper",
    "cardigan",
    "turtleneck",
    "oversized jumper",
    "knitted top",

    "crop top",
    "tank top",
    "vest top",
    "long sleeve top",
    "knitted top",
]


def get_product_urls(page):

    links = page.locator("a").evaluate_all("""
        elements => elements.map(a => a.href)
    """)

    product_urls = []

    for url in links:

        if not url:
            continue

        if not url.startswith("https://www.johnlewis.com/"):
            continue

        # John Lewis product URL:
        # https://www.johnlewis.com/product-name/p123456789

        if not re.search(r"/p\d+(?:[?#]|$)", url):
            continue

        clean_url = url.split("?")[0].split("#")[0]

        if clean_url not in product_urls:
            product_urls.append(clean_url)

        if len(product_urls) == 10:
            break

    return product_urls


with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False
    )

    for keyword in KEYWORDS:

        print("\n" + "=" * 70)
        print("KEYWORD:", keyword)
        print("=" * 70)

        page = browser.new_page(
            viewport={
                "width": 1366,
                "height": 768
            }
        )

        search_url = BASE_URL.format(
            keyword.replace(" ", "+")
        )

        response = None

        try:

            # Try up to 2 times
            for attempt in range(2):

                try:

                    response = page.goto(
                        search_url,
                        wait_until="domcontentloaded",
                        timeout=60000
                    )

                    break

                except Exception as e:

                    if attempt == 0:
                        time.sleep(3)
                    else:
                        raise e

            if response is None:

                print("STATUS: NO RESPONSE")
                page.close()
                continue

            print("STATUS:", response.status)

            # Wait for products to render
            page.wait_for_timeout(5000)

            product_urls = get_product_urls(page)

            print("\nTOP 10 PRODUCT URLS:")

            if len(product_urls) == 0:

                print("NO PRODUCT URLS FOUND")

            else:

                for i, url in enumerate(product_urls, 1):
                    print(f"{i}. {url}")

        except TimeoutError:

            print("STATUS: TIMEOUT")

        except Exception as e:

            error = str(e)

            if "ERR_HTTP2_PROTOCOL_ERROR" in error:
                print("STATUS: HTTP2_ERROR")
            else:
                print("STATUS: FAILED")

        finally:

            try:
                page.close()
            except:
                pass

    browser.close()