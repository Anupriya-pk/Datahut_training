import json
import re
import requests
from bs4 import BeautifulSoup
import settings
from urllib.parse import urljoin


class DataMiningError(Exception):
    """Custom exception for data-mining errors."""


class LidlParser:
    """Parser for Lidl Switzerland website."""

    def __init__(self):
        """Initialize parser requirements."""
        self.url = settings.URL
        self.session = requests.Session()

    
    def start(self):
        """Start the crawling process."""
        print(f"Starting parser for: {self.url}")

        try:
            html = self.fetch_html()
            categories = self.parse_data(html)
            all_products = []
            for category in categories:
                print(
                    f"\nProcessing category: "
                    f"{category['name']}"
                )
                category_html = self.fetch_category_html(
                    category
                )
                products = self.parse_products(
                    category_html
                )
                all_products.extend(products)
                print(
                    f"{category['name']} -> "
                    f"{len(products)} products"
                )
            print(
                f"\nTotal products: {len(all_products)}"
            )

            # List comprehensions
            product_names = [
                product["name"]
                for product in all_products
            ]

            products_with_price = [
                product
                for product in all_products
                if product.get("price") is not None
            ]

            print(
                f"Product names extracted: {len(product_names)}"
            )

            print(
                f"Products with price: {len(products_with_price)}"
            )

            cleaned_data = json.dumps(
                products_with_price,
                ensure_ascii=False,
                indent=2
            )
            self.save_to_file(cleaned_data)
        except DataMiningError as error:
            print(f"Data mining error: {error}")
        finally:
            self.close()


    def fetch_html(self):
        """Fetch HTML from the website."""
        try:
            response = self.session.get(
                self.url,
                timeout=settings.TIMEOUT
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as error:
            raise DataMiningError(
                f"Connection failed: {error}"
            ) from error
        except requests.exceptions.RequestException as error:
            raise DataMiningError(
                f"Invalid response: {error}"
            ) from error
        print("HTML fetched successfully")
        with open(
            settings.RAW_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(response.text)
        print(f"Raw HTML saved to: {settings.RAW_FILE}")
        return response.text


    def parse_products(self, html):
        """Extract product data from a category page."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            product_elements = soup.select(
                "[data-grid-data]"
            )
            products = []
            for element in product_elements:
                raw_data = element.get("data-grid-data")
                if not raw_data:
                    continue
                try:
                    product = json.loads(raw_data)
                except json.JSONDecodeError:
                    continue
                products.append(self.parse_item(product))
            print(
                f"Products found: {len(products)}"
            )
            return products
        except Exception as error:
            raise DataMiningError(
                f"Product parsing failed: {error}"
            ) from error


    def parse_data(self, html):
        """Parse homepage and extract categories."""
        try:
            soup = BeautifulSoup(
                html,
                "html.parser"
            )
            navigation = soup.select_one(
                "#header_navigation_main"
            )
            if navigation is None:
                raise DataMiningError(
                    "Main navigation was not found."
                )
            category_links = navigation.find_all(
                "a",
                attrs={
                    "data-target": re.compile(
                        r"^header/navigation/main/sub[1-7]$"
                    )
                }
            )
            categories = []
            for link in category_links:
                href = link.get("href")
                name_element = link.select_one(
                    ".n-header__main-navigation-link-text"
                )
                if href and name_element:
                    categories.append(
                        {
                            "name": name_element.get_text(
                                strip=True
                            ),
                            "url": (
                                urljoin(self.url, href)
                            )
                        }
                    )
            print(
                f"Categories found: {len(categories)}"
            )
            for category in categories:
                print(f"- {category['name']}")
                print(f"  {category['url']}")
            return categories
        except DataMiningError:
            raise
        except Exception as error:
            raise DataMiningError(
                f"Parsing failed: {error}"
            ) from error


    def fetch_category_html(self, category):
        """Fetch HTML for one category page."""
        try:
            response = self.session.get(
                category["url"],
                timeout=settings.TIMEOUT
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            raise DataMiningError(
                f"Failed to fetch category "
                f"{category['name']}: {error}"
            ) from error
        print(
            f"Category fetched: {category['name']}"
        )
        return response.text


    def parse_item(self, item):
        """Parse and clean one product."""
        price_data = item.get("price") or {}
        return {
            "productId": item.get("productId"),
            "name": item.get("fullTitle"),
            "price": price_data.get("price"),
            "currency": price_data.get("currencyCode"),
            "url": item.get("canonicalPath"),
        }

    
    def save_to_file(self, data):
        """Save parsed data to a text file."""
        with open(
            settings.CLEANED_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(data)

        print(
            f"Cleaned data saved to: "
            f"{settings.CLEANED_FILE}"
        )


    def yield_lines_from_file(self):
        """Yield cleaned data one line at a time."""
        with open(
            settings.CLEANED_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            for line in file:
                yield line.rstrip("\n")



    def close(self):
        """Close the HTTP session."""
        self.session.close()
        print("Parser connection closed")


if __name__ == "__main__":
    parser = LidlParser()
    parser.start()

    