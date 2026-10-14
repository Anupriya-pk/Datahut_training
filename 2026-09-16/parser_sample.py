# # # import requests

# # # url = "https://bh.opensooq.com/en/search/280404989"

# # # headers = {
# # #     "User-Agent": "Mozilla/5.0"
# # # }

# # # response = requests.get(url, headers=headers)

# # # print("Status Code:", response.status_code)

# # # html = response.text

# # # start = html.find('class="text-sm font-light"')

# # # if start != -1:

# # #     end = html.find("</div>", start)

# # #     details = html[start:end]

# # #     details = details.split(">", 1)[1]

# # #     parts = details.split(",")

# # #     print("Bedrooms:", parts[0].strip())

# # #     if len(parts) > 1:
# # #         print("Second:", parts[1].strip())

# # #     if len(parts) > 2:
# # #         print("Area:", parts[2].strip())

# # # else:
# # #     print("Property details not found")




# # # import requests
# # # import time

# # # headers = {
# # #     "User-Agent": "Mozilla/5.0"
# # # }

# # # with open("property_urls.txt", "r", encoding="utf-8") as f:
# # #     urls = [line.strip() for line in f if line.strip()]

# # # print("Total URLs:", len(urls))

# # # for url in urls[:5]:

# # #     print("\nCrawling:", url)

# # #     response = requests.get(url, headers=headers)

# # #     print("Status Code:", response.status_code)

# # #     html = response.text

# # #     # URL
# # #     property_url = url

# # #     # TITLE
# # #     title_start = html.find("<h1")
# # #     title = ""

# # #     if title_start != -1:
# # #         title_end = html.find("</h1>", title_start)

# # #         if title_end != -1:
# # #             title_html = html[title_start:title_end]
# # #             title = title_html.split(">", 1)[1].strip()

# # #     # PROPERTY DETAILS
# # #     details_start = html.find('class="text-sm font-light"')
# # #     details = ""

# # #     if details_start != -1:
# # #         details_end = html.find("</div>", details_start)

# # #         if details_end != -1:
# # #             details_html = html[details_start:details_end]
# # #             details = details_html.split(">", 1)[1].strip()

# # #     parts = details.split(",")

# # #     bedrooms = ""
# # #     bathrooms = ""
# # #     area = ""

# # #     for part in parts:
# # #         part = part.strip()

# # #         if "Bedroom" in part:
# # #             bedrooms = part

# # #         elif "Bathroom" in part:
# # #             bathrooms = part

# # #         elif "m2" in part:
# # #             area = part

# # #     print("URL:", property_url)
# # #     print("Title:", title)
# # #     print("Bedrooms:", bedrooms)
# # #     print("Bathrooms:", bathrooms)
# # #     print("Area:", area)

# # #     time.sleep(1)




# # import requests
# # import time

# # headers = {
# #     "User-Agent": "Mozilla/5.0"
# # }

# # with open("property_urls.txt", "r", encoding="utf-8") as f:
# #     urls = [line.strip() for line in f if line.strip()]

# # print("Total URLs:", len(urls))

# # for url in urls[:5]:

# #     print("\n-----------------------------")
# #     print("Crawling:", url)

# #     response = requests.get(url, headers=headers)

# #     print("Status Code:", response.status_code)

# #     html = response.text

# #     # -------------------------
# #     # URL
# #     # -------------------------

# #     property_url = url

# #     # -------------------------
# #     # TITLE
# #     # -------------------------

# #     title = ""

# #     title_start = html.find("<h1")

# #     if title_start != -1:

# #         title_end = html.find("</h1>", title_start)

# #         if title_end != -1:

# #             title_html = html[title_start:title_end]

# #             if ">" in title_html:
# #                 title = title_html.split(">", 1)[1].strip()

# #     # -------------------------
# #     # PROPERTY DETAILS
# #     # -------------------------

# #     bedrooms = ""
# #     bathrooms = ""
# #     area = ""

# #     details_start = html.find('class="text-sm font-light"')

# #     if details_start != -1:

# #         details_end = html.find("</div>", details_start)

# #         if details_end != -1:

# #             details_html = html[details_start:details_end]

# #             if ">" in details_html:

# #                 details = details_html.split(">", 1)[1].strip()

# #                 parts = details.split(",")

# #                 for part in parts:

# #                     part = part.strip()

# #                     if "Bedroom" in part:
# #                         bedrooms = part

# #                     elif "Bathroom" in part:
# #                         bathrooms = part

# #                     elif "m2" in part:
# #                         area = part

# #     # -------------------------
# #     # OUTPUT
# #     # -------------------------

# #     print("URL:", property_url)
# #     print("Title:", title)
# #     print("Bedrooms:", bedrooms)
# #     print("Bathrooms:", bathrooms)
# #     print("Area:", area)

# #     time.sleep(1)





# import requests
# import time

# headers = {
#     "User-Agent": "Mozilla/5.0"
# }

# # Read URLs
# with open("property_urls.txt", "r", encoding="utf-8") as f:
#     urls = [line.strip() for line in f if line.strip()]

# print("Total URLs:", len(urls))

# for url in urls[:5]:

#     print("\n-----------------------------")
#     print("Crawling:", url)

#     response = requests.get(url, headers=headers)

#     print("Status Code:", response.status_code)

#     html = response.text

#     # --------------------------------
#     # URL
#     # --------------------------------

#     property_url = url

#     # --------------------------------
#     # TITLE
#     # --------------------------------

#     title = ""

#     title_start = html.find("<h1")

#     if title_start != -1:

#         title_start = html.find(">", title_start)

#         if title_start != -1:

#             title_start += 1

#             title_end = html.find("</h1>", title_start)

#             if title_end != -1:

#                 title = html[title_start:title_end].strip()

#     # --------------------------------
#     # PRICE
#     # --------------------------------

#     price = ""

#     price_start = html.find('id="listingViewPriceSelector"')

#     if price_start != -1:

#         price_start = html.find("<span>", price_start)

#         if price_start != -1:

#             price_start += len("<span>")

#             price_end = html.find("</span>", price_start)

#             if price_end != -1:

#                 price = html[price_start:price_end].strip()

#     # --------------------------------
#     # LOCATION
#     # --------------------------------

#     location = ""

#     location_start = html.find('aria-label="Neighborhood:')

#     if location_start != -1:

#         location_start = html.find(">", location_start)

#         if location_start != -1:

#             location_start += 1

#             location_end = html.find("</a>", location_start)

#             if location_end != -1:

#                 location = html[location_start:location_end].strip()

#     # --------------------------------
#     # CITY
#     # --------------------------------

#     city = ""

#     city_start = html.find('aria-label="City:')

#     if city_start != -1:

#         city_start = html.find(">", city_start)

#         if city_start != -1:

#             city_start += 1

#             city_end = html.find("</a>", city_start)

#             if city_end != -1:

#                 city = html[city_start:city_end].strip()

#     # Combine location and city
#     if location and city:
#         location = location + ", " + city

#     # --------------------------------
#     # AREA
#     # --------------------------------

#     area = ""

#     area_start = html.find('aria-label="Area:')

#     if area_start != -1:

#         area_start = html.find(">", area_start)

#         if area_start != -1:

#             area_start += 1

#             area_end = html.find("</a>", area_start)

#             if area_end != -1:

#                 area = html[area_start:area_end].strip()

#     # --------------------------------
#     # BEDROOMS
#     # --------------------------------

#     bedrooms = ""

#     bedroom_start = html.find('aria-label="Bedrooms:')

#     if bedroom_start != -1:

#         bedroom_start = html.find(">", bedroom_start)

#         if bedroom_start != -1:

#             bedroom_start += 1

#             bedroom_end = html.find("</a>", bedroom_start)

#             if bedroom_end != -1:

#                 bedrooms = html[bedroom_start:bedroom_end].strip()

#     # --------------------------------
#     # BATHROOMS
#     # --------------------------------

#     bathrooms = ""

#     bathroom_start = html.find('aria-label="Bathrooms:')

#     if bathroom_start != -1:

#         bathroom_start = html.find(">", bathroom_start)

#         if bathroom_start != -1:

#             bathroom_start += 1

#             bathroom_end = html.find("</a>", bathroom_start)

#             if bathroom_end != -1:

#                 bathrooms = html[bathroom_start:bathroom_end].strip()

#     # --------------------------------
#     # PROPERTY TYPE
#     # --------------------------------

#     property_type = ""

#     property_start = html.find('aria-label="Property Type:')

#     if property_start != -1:

#         property_start = html.find(">", property_start)

#         if property_start != -1:

#             property_start += 1

#             property_end = html.find("</a>", property_start)

#             if property_end != -1:

#                 property_type = html[property_start:property_end].strip()

#     # --------------------------------
#     # PRINT RESULT
#     # --------------------------------

#     print("URL:", property_url)
#     print("Title:", title)
#     print("Price:", price)
#     print("Location:", location)
# #     print("Bedrooms:", bedrooms)
#     print("Bathrooms:", bathrooms)
#     print("Area:", area)

#     time.sleep(1)



import requests
import time

from settings_sample import headers, delay
from items_sample import PropertyItem
from export_sample import export_items


items = []

# Read URLs
with open("property_urls.txt", "r", encoding="utf-8") as f:
    urls = [line.strip() for line in f if line.strip()]

print("Total URLs:", len(urls))


for url in urls:

    print("\n-----------------------------")
    print("Crawling:", url)

    response = requests.get(url, headers=headers)

    print("Status Code:", response.status_code)

    html = response.text

    # --------------------------------
    # TITLE
    # --------------------------------

    title = ""

    title_start = html.find("<h1")

    if title_start != -1:

        title_start = html.find(">", title_start)

        if title_start != -1:

            title_start += 1

            title_end = html.find("</h1>", title_start)

            if title_end != -1:

                title = html[title_start:title_end].strip()

    # --------------------------------
    # PRICE
    # --------------------------------

    price = ""

    price_start = html.find('id="listingViewPriceSelector"')

    if price_start != -1:

        price_start = html.find("<span>", price_start)

        if price_start != -1:

            price_start += len("<span>")

            price_end = html.find("</span>", price_start)

            if price_end != -1:

                price = html[price_start:price_end].strip()

    # --------------------------------
    # LOCATION
    # --------------------------------

    location = ""

    location_start = html.find('aria-label="Neighborhood:')

    if location_start != -1:

        location_start = html.find(">", location_start)

        if location_start != -1:

            location_start += 1

            location_end = html.find("</a>", location_start)

            if location_end != -1:

                location = html[location_start:location_end].strip()

    # --------------------------------
    # CITY
    # --------------------------------

    city = ""

    city_start = html.find('aria-label="City:')

    if city_start != -1:

        city_start = html.find(">", city_start)

        if city_start != -1:

            city_start += 1

            city_end = html.find("</a>", city_start)

            if city_end != -1:

                city = html[city_start:city_end].strip()

    # Combine location + city
    if location and city:
        location = location + ", " + city

    # --------------------------------
    # AREA
    # --------------------------------

    area = ""

    area_start = html.find('aria-label="Area:')

    if area_start != -1:

        area_start = html.find(">", area_start)

        if area_start != -1:

            area_start += 1

            area_end = html.find("</a>", area_start)

            if area_end != -1:

                area = html[area_start:area_end].strip()

    # --------------------------------
    # BEDROOMS
    # --------------------------------

    bedrooms = ""

    bedroom_start = html.find('aria-label="Bedrooms:')

    if bedroom_start != -1:

        bedroom_start = html.find(">", bedroom_start)

        if bedroom_start != -1:

            bedroom_start += 1

            bedroom_end = html.find("</a>", bedroom_start)

            if bedroom_end != -1:

                bedrooms = html[bedroom_start:bedroom_end].strip()

    # --------------------------------
    # BATHROOMS
    # --------------------------------

    bathrooms = ""

    bathroom_start = html.find('aria-label="Bathrooms:')

    if bathroom_start != -1:

        bathroom_start = html.find(">", bathroom_start)

        if bathroom_start != -1:

            bathroom_start += 1

            bathroom_end = html.find("</a>", bathroom_start)

            if bathroom_end != -1:

                bathrooms = html[bathroom_start:bathroom_end].strip()

    # --------------------------------
    # CREATE ITEM
    # --------------------------------

    item = PropertyItem(
        url=url,
        title=title,
        price=price,
        location=location,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        area=area
    )

    items.append(item)

    # --------------------------------
    # PRINT RESULT
    # --------------------------------

    print("URL:", url)
    print("Title:", title)
    print("Price:", price)
    print("Location:", location)
    print("Bedrooms:", bedrooms)
    print("Bathrooms:", bathrooms)
    print("Area:", area)

    time.sleep(delay)


# --------------------------------
# EXPORT
# --------------------------------

export_items(items)

print("\nData exported to output.csv")
