import re
import time
import logging
from urllib.parse import urljoin, urlparse
from parsel import Selector
from settings import (
    HEADERS, BASE_URL, START_URLS, PAGE_PARAM, MAX_PAGES, DELAY,
    request_get,
)
from items import ProductUrlItem, ProductFailedItem

# tile link title looks like: "Chocolate Brown Shower Resistant Hooded Long Padded Puffer Coat (G95338) | £66"
TITLE_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<code>[A-Za-z0-9-]+)\)\s*\|\s*(?P<price>.+)$")
PRICE_RE = re.compile(r"£\s*[\d,]+(?:\.\d+)?")


class Crawler:
    """Crawling Urls"""

    def __init__(self):
        # no mongo / queue: already-saved urls are loaded so a re-run does not duplicate
        self.seen = {row.get("product_url") for row in ProductUrlItem.load()}
        self.total = 0

    def start(self):
        """Requesting Start url"""

        for url in START_URLS:

            meta = {}
            meta['category'] = url
            page = meta.get("page", 1)  # initialising page for pagination

            while True:

                api_url = url if page == 1 else f"{url}?{PAGE_PARAM}={page}"  # generate page Url
                HEADERS['referer'] = url
                logging.info(f"Category page: {api_url}")

                response = request_get(api_url, headers=HEADERS)
                if not response:
                    ProductFailedItem(url=api_url, category=url, page=page).save()
                    break

                is_next = self.parse_item(response, meta)
                if not is_next:
                    logging.info("Pagination completed")
                    break

                # pagination crawling
                if MAX_PAGES and page >= MAX_PAGES:
                    logging.info("MAX_PAGES reached")
                    break
                page += 1
                meta["page"] = page
                time.sleep(DELAY)

    def parse_item(self, response, meta):
        """item part"""

        sel = Selector(text=response.text)

        # XPATH
        # every product tile has a link to /style/<styleId>/<productCode>;
        # its title attribute holds "name (CODE) | £price" (colour swatch links do not match)
        LINK_XPATH = '//a[contains(@href,"/style/")]'
        TITLE_XPATH = './@title'
        URL_XPATH = './@href'

        # EXTRACT
        links = sel.xpath(LINK_XPATH)
        new_found = False
        page_urls = set()
        for link in links:
            title = (link.xpath(TITLE_XPATH).extract_first() or "").strip()
            match = TITLE_RE.match(title)
            if not match:
                continue

            href = link.xpath(URL_XPATH).extract_first()
            url = urljoin(BASE_URL, href)
            url = urlparse(url)._replace(query="", fragment="").geturl()
            if url in page_urls:
                continue
            page_urls.add(url)

            name = match.group("name").strip()
            code = match.group("code").strip()
            prices = PRICE_RE.findall(match.group("price"))
            price = prices[0].replace("£", "").replace(",", "").strip() if prices else ""

            if url in self.seen:
                continue
            self.seen.add(url)
            new_found = True

            # ITEM YEILD
            item = {}
            item['product_url'] = url
            item['name'] = name
            item['product_code'] = code
            item['currency'] = "GBP"
            item['price'] = price
            item['category'] = meta.get('category')
            item['page'] = meta.get('page', 1)
            logging.info(item)
            try:
                ProductUrlItem(**item).save()
                self.total += 1
            except Exception as error:
                logging.error(error)

        # keep paginating only while a page brings new products
        return new_found

    def close(self):
        """Close function for all module object closing"""

        logging.info(f"Crawler finished, new product urls saved: {self.total}")


if __name__ == "__main__":
    crawler = Crawler()
    crawler.start()
    crawler.close()