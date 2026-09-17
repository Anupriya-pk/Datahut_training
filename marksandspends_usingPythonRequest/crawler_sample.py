import re
import time
import requests

from urllib.parse import urljoin, urlparse

from settings_sample import (
    BASE_URL,
    LISTING_URL,
    MAX_PAGES,
    REQUEST_DELAY,
    TIMEOUT,
    HEADERS,
    PRODUCT_URL_FILE,
)


session = requests.Session()
session.headers.update(HEADERS)


def get_listing_url(page_number):

    if page_number == 1:
        return LISTING_URL

    return f"{LISTING_URL}?page={page_number}"


def extract_product_urls(html):

    
    urls = []

    pattern = re.compile(
        r'href\s*=\s*["\']([^"\']+)["\']',
        re.IGNORECASE
    )

    links = pattern.findall(html)

    for link in links:

        link = link.strip()

        if not link:
            continue

        if link.startswith("#"):
            continue

        if link.startswith("javascript:"):
            continue

        full_url = urljoin(BASE_URL, link)

        parsed = urlparse(full_url)

        if parsed.netloc.lower() not in (
            "www.marksandspencer.com",
            "marksandspencer.com",
        ):
            continue

    
        if "/p/clp" not in parsed.path.lower():
            continue

        clean_url = (
            f"{parsed.scheme}://"
            f"{parsed.netloc}"
            f"{parsed.path}"
        )

        
        if clean_url not in urls:
            urls.append(clean_url)

    return urls


def crawl_pages():

    
    all_urls = []

    seen_urls = set()

    for page in range(1, MAX_PAGES + 1):

        url = get_listing_url(page)

        print()
        print("=" * 70)
        print(f"CRAWLING PAGE {page}/{MAX_PAGES}")
        print(url)
        print("=" * 70)

        try:

            response = session.get(
                url,
                timeout=TIMEOUT
            )

            print(
                "STATUS:",
                response.status_code
            )

            if response.status_code != 200:

                print(
                    "Page failed:",
                    response.status_code
                )

                continue

            html = response.text

            page_urls = extract_product_urls(html)

            print(
                "PRODUCT URLs FOUND:",
                len(page_urls)
            )

            new_urls = 0

            for product_url in page_urls:

                if product_url not in seen_urls:

                    seen_urls.add(product_url)

                    all_urls.append(product_url)

                    new_urls += 1

            print(
                "NEW URLs:",
                new_urls
            )

        except requests.RequestException as error:

            print(
                "REQUEST ERROR:",
                error
            )

        time.sleep(REQUEST_DELAY)

    return all_urls


def save_urls(urls):

    with open(
        PRODUCT_URL_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        for url in urls:

            file.write(url + "\n")


def main():

    urls = crawl_pages()

    save_urls(urls)

    print()
    print("=" * 70)
    print("CRAWLING COMPLETED")
    print("=" * 70)

    print(
        "PAGES CRAWLED:",
        MAX_PAGES
    )

    print(
        "TOTAL UNIQUE PRODUCT URLs:",
        len(urls)
    )

    print(
        "SAVED TO:",
        PRODUCT_URL_FILE
    )


if __name__ == "__main__":
    main()