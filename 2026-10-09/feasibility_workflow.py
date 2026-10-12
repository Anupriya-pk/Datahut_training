

from camoufox.sync_api import Camoufox
from urllib.parse import urlparse

SEARCH_URL = (
    "https://www.bestbuy.com/site/searchpage.jsp"
    "?id=pcat17071&st=apple%20airtag%20(2nd%20generation)&intl=nosplash"
)


def open_page(page, url):
    try:
        response = page.goto(url, wait_until="commit", timeout=45000)
        page.wait_for_timeout(2500)
        text = page.locator("body").inner_text(timeout=10000).lower()
        blocked = any(x in text for x in [
            "access denied", "verify you are human", "request blocked"
        ])
        return response, text, bool(
            response and response.status < 400 and text.strip() and not blocked
        )
    except Exception:
        return None, "", False


def main():
    with Camoufox(headless=False) as browser:
        # FIX: Create an explicit context for multiple pages
        context = browser.new_context()
        page = context.new_page()

        # Search page
        _, _, ok = open_page(page, SEARCH_URL)
        print(f"Search page: {SEARCH_URL}\n{'Accessible' if ok else 'Not accessible'}")
        if not ok:
            return

        # Find first AirTag product
        links = page.locator("a[href*='/product/']").evaluate_all(
            "els => els.map(a => ({url:a.href, text:a.innerText || ''}))"
        )
        product_url = next(
            (x["url"] for x in links
             if "airtag" in (x["url"] + x["text"]).lower()), None
        )
        print(f"\nProduct page: {product_url or 'URL not found'}")
        if not product_url:
            return

        _, text, ok = open_page(page, product_url)
        ok = ok and "/product/" in urlparse(page.url).path and "airtag" in (
            page.title() + text
        ).lower()
        print("Accessible" if ok else "Not accessible")
        if not ok:
            return

        # Find review URL on the product page
        product_path = urlparse(product_url).path.rstrip("/").lower()
        links = page.locator("a").evaluate_all("""
            els => els.map(a => ({
                url: a.href,
                text: (a.innerText || a.getAttribute('aria-label') || '').trim().toLowerCase()
            }))
        """)

        review_url = next((
            x["url"] for x in links
            if urlparse(x["url"]).netloc.lower().endswith("bestbuy.com")
            and urlparse(x["url"]).path.rstrip("/").lower() != product_path
            and (
                "/reviews" in urlparse(x["url"]).path.lower()
                or "/review/" in urlparse(x["url"]).path.lower()
                or any(s in x["text"] for s in [
                    "see all customer reviews", "all customer reviews",
                    "see all reviews", "view all reviews"
                ])
            )
            and not any(s in urlparse(x["url"]).path.lower() for s in [
                "write-review", "write-a-review", "submit-review"
            ])
        ), None)

        # If the URL wasn't found, click "See All Customer Reviews"
        review_page = None
        if not review_url:
            previous_pages = context.pages[:]
            old_url = page.url
            try:
                page.get_by_text(
                    "See All Customer Reviews", exact=False
                ).first.click(timeout=7000)
                page.wait_for_timeout(2500)

                new_pages = [p for p in context.pages if p not in previous_pages]
                if new_pages:
                    review_page = new_pages[-1]
                    review_url = review_page.url
                elif page.url != old_url and "review" in page.url.lower():
                    review_page = page
                    review_url = page.url
            except Exception:
                pass

        print(f"\nReview page: {review_url or 'URL not found'}")
        if not review_url:
            return

        # Use the explicit context to open the review URL
        if review_page is None:
            review_page = context.new_page()
            _, review_text, review_ok = open_page(review_page, review_url)
        else:
            try:
                review_text = review_page.locator("body").inner_text(
                    timeout=10000
                ).lower()
                review_ok = bool(review_text.strip())
            except Exception:
                review_text, review_ok = "", False

        review_path = urlparse(review_page.url).path.lower()
        blocked = any(x in review_text for x in [
            "access denied", "verify you are human", "request blocked"
        ])
        review_ok = review_ok and "review" in review_path and not blocked
        print("Accessible" if review_ok else "Not accessible")

        context.close()


if __name__ == "__main__":
    main()


# *************************************************************
# PARSER

from camoufox.sync_api import Camoufox
from parsel import Selector
from urllib.parse import urlencode
import json
import csv

REVIEW_URL = (
    "https://www.bestbuy.com/product/"
    "apple-airtag-1-pack-2nd-generation-2026-white/"
    "JJGCQLTTHZ/sku/6377585/reviews"
)

SKU = "6377585"
MAX_REVIEWS = 200
PAGE_SIZE = 20


def get_summary(selector):
    lines = [
        x.strip()
        for x in selector.xpath("//body//text()").getall()
        if x.strip()
    ]

    summary = {
        "average_rating": "",
        "total_reviews": "",
        "star_5": "",
        "star_4": "",
        "star_3": "",
        "star_2": "",
        "star_1": ""
    }

    text = " ".join(lines)
    phrase = "out of 5 stars with"

    if phrase in text:
        before, after = text.split(phrase, 1)
        parts = before.split()
        remaining = after.strip().split()

        if parts:
            summary["average_rating"] = parts[-1]

        if remaining:
            summary["total_reviews"] = remaining[0].replace(",", "")

    start = next(
        (i for i, line in enumerate(lines)
         if line.lower() == "rating filter"),
        -1
    )

    if start >= 0:
        for i in range(start + 1, len(lines)):
            if lines[i].lower() == "top mentions":
                break

            parts = lines[i].replace(",", "").split()

            if not parts or parts[0] not in ("1", "2", "3", "4", "5"):
                continue

            star = parts[0]
            count = ""

            if len(parts) > 1 and parts[1].isdigit():
                count = parts[1]
            elif i + 1 < len(lines):
                next_line = lines[i + 1].replace(",", "").strip()

                if next_line.isdigit():
                    count = next_line

            if count:
                summary["star_" + star] = count

    return summary


def get_api_page(page, page_number, sort_order):
    params = {
        "page": page_number,
        "pageSize": PAGE_SIZE,
        "sku": SKU,
        "sort": sort_order
    }

    api_url = (
        "https://www.bestbuy.com/ugc/v2/reviews?"
        + urlencode(params)
    )

    result = page.evaluate("""
        async (url) => {
            const response = await fetch(url, {
                method: "GET",
                credentials: "include",
                headers: {
                    "Accept": "application/json, text/plain, */*"
                }
            });

            return {
                status: response.status,
                text: await response.text()
            };
        }
    """, api_url)

    if result["status"] >= 400:
        raise RuntimeError(
            "Review API returned HTTP " + str(result["status"])
        )

    data = json.loads(result["text"])

    return data


def get_reviews(data):
    return (
        data.get("topics")
        or data.get("reviews")
        or data.get("results")
        or []
    )


def parse_review(review):
    badges = review.get("badges") or []

    verified = any(
        "verifiedpurchaser" in (
            str(badge.get("badgeCode", ""))
            + str(badge.get("badgeName", ""))
        ).replace(" ", "").lower()
        for badge in badges
    )

    return {
        "review_id": review.get("id", review.get("reviewId", "")),
        "review_rating": review.get("rating", ""),
        "review_text": review.get("text", ""),
        "review_date": review.get("submissionTime", ""),
        "verified_purchase": "Yes" if verified else "Not indicated"
    }


def main():
    all_reviews = []
    seen = set()
    summary = {}

    with Camoufox(headless=False) as browser:
        page = browser.new_page()
        page.set_default_timeout(15000)

        response = page.goto(
            REVIEW_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(3000)

        if not response or response.status >= 400:
            print("Review page: Not accessible")
            return

        print("Review page: Accessible")

        # Parse product rating summary using Parsel.
        selector = Selector(text=page.content())
        summary = get_summary(selector)

        # Try the product page's default sorting first.
        sort_order = "MOST_RELEVANT"

        try:
            first_data = get_api_page(page, 1, sort_order)
            first_reviews = get_reviews(first_data)

            # Fallback if the selected sort returns no records.
            if not first_reviews:
                sort_order = "MOST_RECENT"
                first_data = get_api_page(page, 1, sort_order)
                first_reviews = get_reviews(first_data)

        except Exception as error:
            print("Review API error:", str(error).splitlines()[0])
            return

        if not first_reviews:
            print("No review records returned.")
            return

        total_pages = first_data.get("totalPages", 1)
        pages_needed = min(
            total_pages,
            (MAX_REVIEWS + PAGE_SIZE - 1) // PAGE_SIZE
        )

        for page_number in range(1, pages_needed + 1):
            try:
                if page_number == 1:
                    data = first_data
                else:
                    data = get_api_page(
                        page, page_number, sort_order
                    )

                records = get_reviews(data)
                added = 0

                for item in records:
                    review = parse_review(item)

                    # Ignore empty review text.
                    if not review["review_text"]:
                        continue

                    key = review["review_id"] or (
                        review["review_rating"],
                        review["review_date"],
                        review["review_text"]
                    )

                    if key in seen:
                        continue

                    seen.add(key)
                    all_reviews.append(review)
                    added += 1

                    if len(all_reviews) >= MAX_REVIEWS:
                        break

                print(
                    "Page", page_number,
                    "| New reviews:", added,
                    "| Total:", len(all_reviews)
                )

                if len(all_reviews) >= MAX_REVIEWS:
                    break

                if not records:
                    break

            except Exception as error:
                print(
                    "Page", page_number, "failed:",
                    str(error).splitlines()[0]
                )
                break

    fields = [
        "review_number",
        "product_url",
        "average_rating",
        "total_reviews",
        "star_5",
        "star_4",
        "star_3",
        "star_2",
        "star_1",
        "review_rating",
        "review_text",
        "review_date",
        "verified_purchase",
        "review_id"
    ]

    with open(
        "reviews.csv",
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for number, review in enumerate(all_reviews, start=1):
            writer.writerow({
                "review_number": number,
                "product_url": REVIEW_URL,
                **summary,
                **review
            })

    print("Reviews collected:", len(all_reviews))
    print("Saved: reviews.csv")


if __name__ == "__main__":
    main()