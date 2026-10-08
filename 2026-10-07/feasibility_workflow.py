
import re
import csv
import time
import requests
from datetime import datetime
from scrapy import Selector

BASE = 'https://mmlafleur.com'
START_URL = f'{BASE}/collections/tops'
CATEGORY = 'tops'
LOOX_ID = 'qRD5si0H9T'
OUT_FILE = 'mmlafleur_tops_reviews.csv'
OUT_DEDUP = 'mmlafleur_tops_reviews_dedup.csv'
headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0'}

FIELDS = ['url', 'product_sku', 'product_name', 'brand', 'original_price', 'sale_price', 'category',
          'total_number_of_reviews', '1_star', '2_star', '3_star', '4_star', '5_star',
          'date_of_purchase', 'place_of_purchase', 'review_title', 'review_text',
          'review_id']  


# ---------------- CRAWLER ----------------
def get_product_urls():
    urls, page = [], 1
    while True:
        r = requests.get(f'{START_URL}/products.json', params={'limit': 250, 'page': page},
                         headers=headers, timeout=30)
        products = r.json().get('products', [])
        if not products:
            break
        urls += [f"{BASE}/products/{p['handle']}" for p in products]
        page += 1
    return list(dict.fromkeys(urls))


# ---------------- PARSER ----------------
def parse_product(url):
    p = requests.get(url + '.js', headers=headers, timeout=30).json()
    v = p['variants'][0]
    product = {
        'url': url,
        'product_sku': v.get('sku', ''),
        'product_name': p.get('title', ''),
        'brand': p.get('vendor', ''),
        'original_price': (v['compare_at_price'] or v['price']) / 100,
        'sale_price': v['price'] / 100,
        'category': CATEGORY,
    }
    return p['id'], product


def parse_reviews(product_id):
    reviews, seen, page = [], set(), 1
    while page <= 50:   # safety
        r = requests.get(f'https://loox.io/widget/{LOOX_ID}/reviews/{product_id}',
                         params={'limit': 10, 'page': page}, headers=headers, timeout=30)
        items = Selector(text=r.text).xpath('//div[@data-id][@class="grid-item"]')
        new = [it for it in items if it.xpath('@data-id').get() not in seen]
        if not new:
            break
        for it in new:
            rid = it.xpath('@data-id').get()
            seen.add(rid)
            ts = it.xpath('.//div[contains(@class,"time")]/@data-time').get()
            label = it.xpath('.//div[contains(@class,"stars")]//span/@aria-label').get() or ''
            m = re.search(r'(\d) / 5', label)
            raw = it.xpath('.//div[contains(@class,"main-text")]//text()').getall()
            lines = [x.strip() for t in raw for x in t.split('\n') if x.strip()]
            reviews.append({
                'review_id': rid,
                'rating': int(m.group(1)) if m else None,
                'date': datetime.fromtimestamp(int(ts) / 1000).strftime('%Y-%m-%d') if ts else '',
                'title': lines[0] if len(lines) > 1 else '',
                'text': ' '.join(lines[1:] if len(lines) > 1 else lines),
            })
        page += 1
    return reviews


# ---------------- MAIN ----------------
urls = get_product_urls()
# urls = urls[:5]
print('TOTAL PRODUCTS:', len(urls))

with open(OUT_FILE, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()

    for n, url in enumerate(urls, 1):
        try:
            pid, product = parse_product(url)
            reviews = parse_reviews(pid)
        except Exception as e:
            print(f'[{n}/{len(urls)}] FAILED {url}: {e}')
            continue

        star = {k: sum(1 for x in reviews if x['rating'] == k) for k in range(1, 6)}
        summary = {'total_number_of_reviews': len(reviews),
                   '1_star': star[1], '2_star': star[2], '3_star': star[3],
                   '4_star': star[4], '5_star': star[5]}

        if not reviews:  
            reviews = [{'review_id': '', 'date': '', 'title': '', 'text': ''}]

        for x in reviews:
            writer.writerow({**product, **summary,
                             'date_of_purchase': x['date'],  
                             'place_of_purchase': '',         
                             'review_title': x['title'],
                             'review_text': x['text'],
                             'review_id': x['review_id']})
        f.flush()
        print(f'[{n}/{len(urls)}] {product["product_name"]} -> {summary["total_number_of_reviews"]} reviews')
        time.sleep(0.5)

print('Saved:', OUT_FILE)


# --------------------------------
with open(OUT_FILE, newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

seen_ids, dedup = set(), []
for row in rows:
    rid = row['review_id']
    if rid == '':               
        dedup.append(row)
    elif rid not in seen_ids:
        seen_ids.add(rid)
        dedup.append(row)

with open(OUT_DEDUP, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(dedup)

print(f'All rows: {len(rows)} | Unique reviews: {len(seen_ids)} | Dedup rows: {len(dedup)}')
print('Saved:', OUT_DEDUP)