
import warnings
warnings.filterwarnings("ignore", message="Python 3.8 is no longer supported.*")

import requests
from scrapy import Selector
import json
import csv
import re
from urllib.parse import urljoin, urlparse

############################## SETTINGS ##############################

BASE_URL = "https://www.afcurgentcare.com/"
SEARCH_URL = BASE_URL + "locations/"
API_URL = BASE_URL + "_api/locations_search/"

ZIP_CODES = ["02116", "80203", "19123", "37919", "37211"]

CSV_FILE = "afc_clinic_data.csv"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:128.0) "
        "Gecko/20100101 Firefox/128.0"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9"
}

clinic_urls = set()


############################## HELPER FUNCTIONS ##############################

def clean_text(value):
    return " ".join(value.split()) if value else ""


def get_clinic_url(url):
    if not isinstance(url, str) or not url.strip():
        return None

    parsed = urlparse(urljoin(BASE_URL, url.strip()))

    if parsed.hostname not in [
        "www.afcurgentcare.com",
        "afcurgentcare.com"
    ]:
        return None

    path = parsed.path.rstrip("/").lower()

    if not path or path == "/locations":
        return None

    excluded = [
        "/_api/", "/wp-content/", "/wp-json/",
        "/patient-services/", "/services/", "/resources/",
        "/locations/", "/careers/"
    ]

    if any(path.startswith(item) for item in excluded):
        return None

    if any(word in path for word in [
        "staging", "preview", "test-page"
    ]):
        return None

    return parsed._replace(query="", fragment="").geturl()


def extract_json_urls(data):
    urls = set()

    url_keys = [
        "url", "href", "link", "path", "permalink",
        "clinic_url", "clinicurl", "location_url",
        "locationurl", "page_url", "details_url",
        "canonical_url"
    ]

    if isinstance(data, dict):
        for key, value in data.items():
            if key.lower() in url_keys and isinstance(value, str):
                clinic_url = get_clinic_url(value)
                if clinic_url:
                    urls.add(clinic_url)
            elif isinstance(value, (dict, list)):
                urls.update(extract_json_urls(value))

    elif isinstance(data, list):
        for item in data:
            urls.update(extract_json_urls(item))

    return urls


def find_business_data(data, business_list):
    if isinstance(data, dict):
        types = data.get("@type", [])

        if isinstance(types, str):
            types = [types]

        business_types = [
            "LocalBusiness", "MedicalClinic",
            "MedicalBusiness", "MedicalOrganization"
        ]

        if any(item in business_types for item in types):
            business_list.append(data)

        for value in data.values():
            if isinstance(value, (dict, list)):
                find_business_data(value, business_list)

    elif isinstance(data, list):
        for item in data:
            find_business_data(item, business_list)


def parse_address_from_page(lines):
    street_address = city = state = zip_code = ""

    for index, line in enumerate(lines):
        if "," not in line:
            continue

        parts = line.rsplit(",", 1)

        if len(parts) != 2:
            continue

        possible_city = parts[0].strip()
        state_zip = parts[1].strip().split()

        if len(state_zip) < 2:
            continue

        possible_state = state_zip[0]
        possible_zip = state_zip[1]

        if (
            len(possible_state) == 2
            and possible_state.isalpha()
            and possible_zip.split("-")[0].isdigit()
            and len(possible_zip.split("-")[0]) == 5
        ):
            city = possible_city
            state = possible_state
            zip_code = possible_zip

            for previous_line in reversed(
                lines[max(0, index - 4):index]
            ):
                if (
                    any(char.isdigit() for char in previous_line)
                    and any(char.isalpha() for char in previous_line)
                    and not previous_line.lower().startswith("call ")
                ):
                    street_address = previous_line
                    break

            if street_address:
                break

    return street_address, city, state, zip_code


def contains_price(text):
    return bool(
        re.search(r"\$\s?\d+(?:,\d{3})*(?:\.\d{2})?", text)
    )


############################## CRAWLER ##############################

try:
    response = requests.get(
        BASE_URL,
        headers=headers,
        timeout=30
    )

    if response.status_code == 200:
        for zip_code in ZIP_CODES:
            try:
                response = requests.get(
                    SEARCH_URL,
                    params={"near_location": zip_code},
                    headers=headers,
                    timeout=30
                )

                if response.status_code != 200:
                    continue

                response = requests.get(
                    API_URL,
                    params={"near_location": zip_code},
                    headers=headers,
                    timeout=30
                )

                if response.status_code == 200:
                    try:
                        clinic_urls.update(
                            extract_json_urls(response.json())
                        )
                    except ValueError:
                        pass

            except requests.RequestException:
                continue

except requests.RequestException:
    pass


############################## PARSER ##############################

clinic_rows = []
seen_addresses = set()

for clinic_url in sorted(clinic_urls):
    try:
        response = requests.get(
            clinic_url,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            continue

        selector = Selector(text=response.text)

        page_title = selector.xpath(
            "//title/text()"
        ).get(default="").strip().lower()

        if any(word in page_title for word in [
            "page not found",
            "404 not found",
            "page does not exist"
        ]):
            continue

        final_url = get_clinic_url(response.url)

        if not final_url:
            continue

        page_lines = [
            clean_text(text)
            for text in selector.xpath(
                "//body//text()[normalize-space()]"
            ).getall()
            if clean_text(text)
        ]

        page_text = " ".join(page_lines)

        ############################## CLINIC NAME ##############################

        clinic_name = ""
        business_objects = []

        scripts = selector.xpath(
            '//script[@type="application/ld+json"]/text()'
        ).getall()

        for script in scripts:
            try:
                find_business_data(
                    json.loads(script),
                    business_objects
                )
            except (ValueError, TypeError):
                continue

        business_objects.sort(
            key=lambda item: (
                bool(item.get("address")),
                bool(item.get("telephone")),
                bool(item.get("name"))
            ),
            reverse=True
        )

        business_data = (
            business_objects[0] if business_objects else {}
        )

        clinic_name = clean_text(
            business_data.get("name", "")
        )

        if not clinic_name:
            page_title = clean_text(
                selector.xpath("//title/text()").get(default="")
            )

            if "|" in page_title:
                clinic_name = page_title.split("|")[-1].strip()
            else:
                clinic_name = clean_text(
                    " ".join(
                        selector.xpath("//h1//text()").getall()
                    )
                )

        ############################## ADDRESS ##############################

        street_address = ""
        city = ""
        state = ""
        zip_code = ""

        address_data = business_data.get("address", {})

        if isinstance(address_data, list):
            address_data = address_data[0] if address_data else {}

        if isinstance(address_data, dict):
            street_address = clean_text(
                address_data.get("streetAddress", "")
            )
            city = clean_text(
                address_data.get("addressLocality", "")
            )
            state = clean_text(
                address_data.get("addressRegion", "")
            )
            zip_code = clean_text(
                address_data.get("postalCode", "")
            )

        if not all([street_address, city, state, zip_code]):
            parsed_address = parse_address_from_page(page_lines)

            if not street_address:
                street_address = parsed_address[0]
            if not city:
                city = parsed_address[1]
            if not state:
                state = parsed_address[2]
            if not zip_code:
                zip_code = parsed_address[3]

        ############################## PHONE NUMBER ##############################

        phone_number = clean_text(
            business_data.get("telephone", "")
        )

        if not phone_number:
            phone_links = selector.xpath(
                '//a[starts-with(@href, "tel:")]/@href'
            ).getall()

            if phone_links:
                phone_number = phone_links[0].replace(
                    "tel:", "", 1
                ).strip()

        if not phone_number:
            phone_match = re.search(
                r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}",
                page_text
            )

            if phone_match:
                phone_number = phone_match.group(0)

        ############################## PRICE LISTED ##############################

        price_listed = "No"

        if contains_price(page_text):
            price_listed = "Yes"

        else:
            price_keywords = [
                "pricing", "price", "self-pay",
                "self pay", "cost", "fees", "fee"
            ]

            pricing_urls = set()

            for link in selector.xpath("//a[@href]"):
                href = link.xpath("./@href").get()

                link_text = clean_text(
                    " ".join(link.xpath(".//text()").getall())
                )

                if not href:
                    continue

                details = (link_text + " " + href).lower()

                if any(word in details for word in price_keywords):
                    pricing_url = urljoin(final_url, href)
                    parsed_url = urlparse(pricing_url)

                    if (
                        parsed_url.scheme in ["http", "https"]
                        and parsed_url.netloc == urlparse(final_url).netloc
                        and pricing_url != final_url
                    ):
                        pricing_urls.add(pricing_url)

            for pricing_url in sorted(pricing_urls)[:5]:
                try:
                    price_response = requests.get(
                        pricing_url,
                        headers=headers,
                        timeout=30
                    )

                    if price_response.status_code != 200:
                        continue

                    price_selector = Selector(
                        text=price_response.text
                    )

                    price_text = " ".join(
                        price_selector.xpath(
                            "//body//text()[normalize-space()]"
                        ).getall()
                    )

                    if contains_price(price_text):
                        price_listed = "Yes"
                        break

                except requests.RequestException:
                    continue

        ############################## REMOVE DUPLICATES ##############################

        address_key = " ".join([
            street_address, city, state, zip_code
        ]).strip().lower()

        dedup_key = (
            address_key
            if all([street_address, city, state, zip_code])
            else final_url.lower()
        )

        if dedup_key in seen_addresses:
            continue

        seen_addresses.add(dedup_key)

        ############################## STORE DATA ##############################

        clinic_rows.append({
            "clinic_name": clinic_name,
            "street_address": street_address,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "phone_number": phone_number,
            "clinic_page_url": final_url,
            "price_listed": price_listed
        })

    except requests.RequestException:
        continue


############################## SAVE CSV ##############################

fieldnames = [
    "clinic_name",
    "street_address",
    "city",
    "state",
    "zip_code",
    "phone_number",
    "clinic_page_url",
    "price_listed"
]

with open(
    CSV_FILE,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(clinic_rows)


############################## FINDINGS ##############################

print("CSV file saved")