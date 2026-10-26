import re
import json
import time
import logging
from html import unescape
from urllib.parse import urlparse
from parsel import Selector
from settings import HEADERS, DELAY, MAX_PRODUCTS, request_get, EXTRACTION_DATE
from items import ProductItem, ProductUrlItem, ProductFailedItem

IMAGE_RE = re.compile(r'https?://xcdn\.next\.co\.uk/[^"\'\s\\<>]+?\.(?:jpg|jpeg|png|webp)', re.I)
PRICE_RE = re.compile(r"£\s*([\d,]+(?:\.\d+)?)")


class Parser:
    """parser"""

    def __init__(self):
        # no queue / mongo: urls come from the crawler file, finished urls are skipped on re-run
        self.done = {row.get("url") for row in ProductItem.load()}
        self.total = 0

    def start(self):
        """start code"""

        metas = ProductUrlItem.load()
        if MAX_PRODUCTS:
            metas = metas[:MAX_PRODUCTS]
        logging.info(f"Product urls to parse: {len(metas)}")

        for meta in metas:
            url = meta.get('product_url')
            if not url or url in self.done:
                continue
            response = request_get(url, headers=HEADERS)
            if response:
                self.parse_item(url, response, meta)
                self.done.add(url)
                time.sleep(DELAY)
            else:
                ProductFailedItem(url=url).save()

    @staticmethod
    def _find_product_ld(sel):
        """Return the schema.org Product dict from JSON-LD, or {}"""
        for text in sel.xpath('//script[@type="application/ld+json"]/text()').extract():
            try:
                data = json.loads(text)
            except ValueError:
                continue
            stack = data if isinstance(data, list) else [data]
            while stack:
                node = stack.pop()
                if isinstance(node, dict):
                    node_type = node.get("@type")
                    types = node_type if isinstance(node_type, list) else [node_type]
                    if "Product" in types:
                        return node
                    stack.extend(node.get("@graph", []))
                elif isinstance(node, list):
                    stack.extend(node)
        return {}

    def parse_item(self, url, response, meta):
        """item part"""

        sel = Selector(text=response.text)

        # XPATH
        PRODUCT_NAME_XPATH = '//h1//text()'
        OG_TITLE_XPATH = '//meta[@property="og:title"]/@content'
        DESCRIPTION_XPATH = '//meta[@name="description"]/@content'
        BREADCRUMBS_XPATH = '//nav[contains(@aria-label,"readcrumb")]//li|//ol[contains(@class,"readcrumb")]//li'
        COLOUR_XPATH = '//*[@data-testid="colour-selector"]//text()|//*[contains(@class,"colour")]//option[@selected]/text()'
        SIZE_XPATH = '//select[contains(@id,"ize") or contains(@name,"ize")]/option/text()'
        PRICE_META_XPATH = '//meta[@property="product:price:amount"]/@content|//meta[@property="og:price:amount"]/@content'
        PRODUCT_CODE_REGEX = r'Product Code:?\s*([A-Z0-9-]{5,12})'

        # EXTRACT
        ld = self._find_product_ld(sel)
        offers = ld.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        brand = ld.get("brand") or ""
        if isinstance(brand, dict):
            brand = brand.get("name", "")
        rating_ld = ld.get("aggregateRating") or {}

        product_name = ld.get("name") or " ".join(
            x.strip() for x in sel.xpath(PRODUCT_NAME_XPATH).extract() if x.strip()
        ) or (sel.xpath(OG_TITLE_XPATH).extract_first() or "")
        description = ld.get("description") or sel.xpath(DESCRIPTION_XPATH).extract_first() or ""
        breadcrumbs_list = sel.xpath(BREADCRUMBS_XPATH)
        colour = (ld.get("color") or sel.xpath(COLOUR_XPATH).extract_first() or "").strip()
        sizes = [x.strip() for x in sel.xpath(SIZE_XPATH).extract() if x.strip()]
        sizes = [x for x in sizes if not x.lower().startswith("choose")]

        price = offers.get("price") or offers.get("lowPrice") or sel.xpath(PRICE_META_XPATH).extract_first() or ""
        if not price:  # fall back to the price shown in the tile title saved by the crawler
            price = meta.get("price", "")
        currency = offers.get("priceCurrency") or "GBP"

        code = ld.get("sku") or ld.get("mpn") or ""
        page_text = " ".join(sel.xpath("//body//text()").extract())
        code_match = re.search(PRODUCT_CODE_REGEX, page_text)
        product_code = (code_match.group(1) if code_match else "") or meta.get("product_code", "") \
            or urlparse(url).path.rstrip("/").split("/")[-1].upper()
        product_code = product_code.replace("-", "").upper()  # G95-338 -> G95338

        # CLEAN
        product_name = unescape(product_name).strip()
        description = re.sub(r"<.*?>|\s+", " ", unescape(description)).strip()
        breadcrumbs = []
        for breadcrumb in breadcrumbs_list:
            value = breadcrumb.xpath(".//text()").extract()
            if value:
                value = " ".join(x.strip() for x in value if x.strip())
                if value:
                    breadcrumbs.append(value)
        breadcrumbs = (">".join(breadcrumbs)).strip() if breadcrumbs else ""

        # images: JSON-LD first, then any product image url on the page; strip resize query
        images = ld.get("image") or []
        images = [images] if isinstance(images, str) else list(images)
        images += IMAGE_RE.findall(response.text)
        clean_images = []
        for image in images:
            image = image.split("?")[0].strip()
            if image and "/itemimages/" in image.lower() and "swatch" not in image.lower() \
                    and image not in clean_images:
                clean_images.append(image)

        rating = rating_ld.get("ratingValue", "")
        review = rating_ld.get("reviewCount", rating_ld.get("ratingCount", ""))

        # ITEM YEILD
        item = {}
        item["website"] = "Next"
        item["url"] = url
        item["product_name"] = product_name
        item["brand"] = brand or "Next"
        item["product_code"] = product_code
        item["sku"] = code
        item["price"] = str(price).replace(",", "")
        item["currency"] = currency
        item["description"] = description
        item["color"] = colour
        item["sizes"] = sizes
        item["breadcrumbs"] = breadcrumbs
        item["category"] = meta.get("category", "")
        item["rating"] = str(rating) if rating else ""
        item["review"] = str(review) if review else ""
        item["images"] = clean_images[:6]
        item["extraction_date"] = EXTRACTION_DATE

        logging.info(item)
        try:
            ProductItem(**item).save()
            self.total += 1
        except Exception as error:
            logging.error(error)

    def close(self):
        """connection close"""

        logging.info(f"Parser finished, products saved: {self.total}")


if __name__ == "__main__":
    parser_obj = Parser()
    parser_obj.start()
    parser_obj.close()