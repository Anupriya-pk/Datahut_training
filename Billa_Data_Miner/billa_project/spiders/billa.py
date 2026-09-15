import scrapy
import re
import json


class BillaSpider(scrapy.Spider):
    name = "billa"
    allowed_domains = ["shop.billa.at"]

    start_urls = [
        "https://shop.billa.at/kategorie?page=1"
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "FEED_EXPORT_ENCODING": "utf-8",
    }

    def parse(self, response):

        # -----------------------------------------
        # FIND PRODUCT LINKS
        # -----------------------------------------

        product_links = response.xpath(
            '//a[contains(@href, "/produkte/")]/@href'
        ).getall()

        # Remove duplicates
        product_links = list(dict.fromkeys(product_links))

        self.logger.info(
            "PRODUCT LINKS FOUND: %d",
            len(product_links)
        )

        for link in product_links:
            yield response.follow(
                link,
                callback=self.parse_product
            )

        # -----------------------------------------
        # PAGINATION
        # -----------------------------------------

        current_page = response.url

        match = re.search(r"page=(\d+)", current_page)

        if match:
            page = int(match.group(1))
        else:
            page = 1

        next_page = page + 1

        next_url = f"https://shop.billa.at/kategorie?page={next_page}"

        # Stop when there are no product links
        if product_links:
            yield scrapy.Request(
                next_url,
                callback=self.parse
            )

    def parse_product(self, response):

        url = response.url

        # -----------------------------------------
        # PRODUCT ID
        # -----------------------------------------

        match = re.search(
            r"-(\d+)(?:/?$)",
            url
        )

        product_id = match.group(1) if match else ""

        # -----------------------------------------
        # PRODUCT NAME
        # -----------------------------------------

        name = response.xpath(
            "//h1[1]//text()[normalize-space()]"
        ).getall()

        name = " ".join(
            x.strip()
            for x in name
            if x.strip()
        )

        # Remove duplicated name if necessary
        if name:
            words = name.split()

            half = len(words) // 2

            if (
                half > 0
                and " ".join(words[:half])
                == " ".join(words[half:])
            ):
                name = " ".join(words[:half])

        # -----------------------------------------
        # PRODUCT IMAGE
        # -----------------------------------------

        image = response.xpath(
            '//meta[@property="og:image"]/@content'
        ).get()

        if not image:
            image = response.xpath(
                '//img[@alt and @src][1]/@src'
            ).get()

        if image:
            image = response.urljoin(image)

        # -----------------------------------------
        # DESCRIPTION
        # -----------------------------------------

        description = response.xpath(
            '//meta[@name="description"]/@content'
        ).get()

        # -----------------------------------------
        # PRODUCT ARTICLE NUMBER
        # -----------------------------------------

        article_number = response.xpath(
            '//*[contains(text(), "Art. Nr.")]/text()'
        ).get()

        if article_number:
            article_number = article_number.strip()

        # -----------------------------------------
        # EAN
        # -----------------------------------------

        ean = ""

        # Look for EAN-related text
        ean_matches = response.xpath(
            '//*[contains(translate(text(), '
            '"EAN", "ean"), "ean")]/text()'
        ).getall()

        for value in ean_matches:
            value = value.strip()

            numbers = re.findall(
                r"\b\d{8,14}\b",
                value
            )

            if numbers:
                ean = numbers[0]
                break

        # -----------------------------------------
        # PRICE
        # -----------------------------------------

        price = ""

        # First try common price elements
        price_candidates = response.xpath(
            '''
            //main//*[contains(@class, "price")]
            //text()
            '''
        ).getall()

        for value in price_candidates:

            value = value.strip()

            if re.search(r"\d+[,.]\d{2}\s*€", value):

                price = value
                break

        # -----------------------------------------
        # FALLBACK PRICE
        # -----------------------------------------

        if not price:

            # Only inspect main product area,
            # not the entire body.
            main_text = response.xpath(
                "//main//text()[normalize-space()]"
            ).getall()

            for value in main_text:

                value = value.strip()

                if re.fullmatch(
                    r"\d+[,.]\d{2}\s*€",
                    value
                ):
                    price = value
                    break

        # -----------------------------------------
        # UNIT PRICE
        # -----------------------------------------

        unit_price = ""

        unit_matches = response.xpath(
            '''
            //main//text()[
                contains(., "1 Liter")
                or contains(., "1 kg")
                or contains(., "1 kg")
                or contains(., "100 g")
            ]
            '''
        ).getall()

        for value in unit_matches:

            value = value.strip()

            if value:
                unit_price = value
                break

        # -----------------------------------------
        # QUANTITY / PACKAGE SIZE
        # -----------------------------------------

        quantity = ""

        quantity_matches = response.xpath(
            '''
            //main//text()[
                contains(., "ml")
                or contains(., "Liter")
                or contains(., "g")
                or contains(., "kg")
            ]
            '''
        ).getall()

        for value in quantity_matches:

            value = value.strip()

            if re.search(
                r"\b\d+(?:[,.]\d+)?\s*(ml|l|liter|g|kg)\b",
                value,
                re.I
            ):
                quantity = value
                break

        # -----------------------------------------
        # BRAND
        # -----------------------------------------

        brand = ""

        # Try structured brand metadata
        brand = response.xpath(
            '//meta[@property="product:brand"]/@content'
        ).get()

        if not brand:
            brand = response.xpath(
                '//meta[@name="brand"]/@content'
            ).get()

        if not brand:
            brand = ""

        # -----------------------------------------
        # OUTPUT
        # -----------------------------------------

        yield {
            "product_id": product_id,
            "product_name": name,
            "brand": brand,
            "price": price,
            "unit_price": unit_price,
            "quantity": quantity,
            "ean": ean,
            "article_number": article_number,
            "description": description,
            "image": image,
            "product_url": url,
        }