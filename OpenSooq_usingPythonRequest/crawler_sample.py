# # import requests
# # from bs4 import BeautifulSoup
# # from urllib.parse import urljoin

# # BASE_URL = "https://bh.opensooq.com"
# # START_URL = "https://bh.opensooq.com/en/property"

# # headers = {
# #     "User-Agent": "Mozilla/5.0"
# # }

# # page_number = 1
# # all_urls = []

# # while True:

# #     url = START_URL if page_number == 1 else f"{START_URL}?page={page_number}"

# #     print(f"Crawling page {page_number}: {url}")

# #     response = requests.get(url, headers=headers)

# #     print("Status Code:", response.status_code)

# #     if response.status_code != 200:
# #         print("Failed to crawl page")
# #         break

# #     soup = BeautifulSoup(response.text, "html.parser")

# #     page_urls = []

# #     for link in soup.find_all("a", href=True):

# #         href = link["href"]

# #         full_url = urljoin(BASE_URL, href)

# #         if "/en/search/" in full_url:
# #             if full_url not in page_urls:
# #                 page_urls.append(full_url)

# #     print("URLs found:", len(page_urls))

# #     if not page_urls:
# #         print("No more property URLs found.")
# #         break

# #     for property_url in page_urls:
# #         if property_url not in all_urls:
# #             all_urls.append(property_url)

# #     page_number += 1


# # with open("property_urls.txt", "w", encoding="utf-8") as f:

# #     for url in all_urls:
# #         f.write(url + "\n")


# # print("--------------------------------")
# # print("Total URLs:", len(all_urls))
# # print("URLs saved to property_urls.txt")




# import requests
# import re

# START_URL = "https://bh.opensooq.com/en/property"

# headers = {
#     "User-Agent": "Mozilla/5.0"
# }

# page_number = 1
# all_urls = []

# while True:

#     if page_number == 1:
#         url = START_URL
#     else:
#         url = f"{START_URL}?page={page_number}"

#     print(f"Crawling page {page_number}: {url}")

#     response = requests.get(url, headers=headers)

#     print("Status Code:", response.status_code)

#     if response.status_code != 200:
#         print("Failed to crawl page")
#         break

#     html = response.text

#     # Find all href values
#     hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)

#     page_urls = []

#     for href in hrefs:

#         # Convert relative URL to full URL
#         if href.startswith("/"):
#             full_url = "https://bh.opensooq.com" + href
#         elif href.startswith("https://bh.opensooq.com"):
#             full_url = href
#         else:
#             continue

#         # Keep only property listing URLs
#         if "/en/search/" in full_url:

#             if full_url not in page_urls:
#                 page_urls.append(full_url)

#     print("URLs found:", len(page_urls))

#     # Stop when no property URLs are found
#     if not page_urls:
#         print("No more property URLs found.")
#         break

#     for property_url in page_urls:

#         if property_url not in all_urls:
#             all_urls.append(property_url)

#     page_number += 1


# # Save all property URLs
# with open("property_urls.txt", "w", encoding="utf-8") as f:

#     for property_url in all_urls:
#         f.write(property_url + "\n")


# print("--------------------------------")
# print("Total URLs:", len(all_urls))
# print("URLs saved to property_urls.txt")






import requests
import re


START_URL = "https://bh.opensooq.com/en/property"


headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "cache-control": "max-age=0",
    "priority": "u=0, i",
    "referer": "https://bh.opensooq.com/en/property",
    "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
}


page_number = 1
all_urls = []


while True:

    if page_number == 1:
        url = START_URL
    else:
        url = f"{START_URL}?page={page_number}"

    print(f"Crawling page {page_number}: {url}")

    response = requests.get(
        url,
        headers=headers
    )

    print("Status Code:", response.status_code)

    if response.status_code != 200:
        print("Failed to crawl page")
        break

    html = response.text

    # Find all href values
    hrefs = re.findall(
        r'href=["\']([^"\']+)["\']',
        html
    )

    page_urls = []

    for href in hrefs:

        if href.startswith("/"):
            full_url = "https://bh.opensooq.com" + href

        elif href.startswith("https://bh.opensooq.com"):
            full_url = href

        else:
            continue

        # Keep only property listing URLs
        if "/en/search/" in full_url:

            if full_url not in page_urls:
                page_urls.append(full_url)

    print("URLs found:", len(page_urls))

    if not page_urls:
        print("No more property URLs found.")
        break

    for property_url in page_urls:

        if property_url not in all_urls:
            all_urls.append(property_url)

    page_number += 1


# Save all property URLs
with open("property_urls.txt", "w", encoding="utf-8") as f:

    for property_url in all_urls:
        f.write(property_url + "\n")


print("--------------------------------")
print("Total URLs:", len(all_urls))
print("URLs saved to property_urls.txt")

