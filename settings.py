import sys
import json
import itertools
from datetime import datetime
import os
import time
import calendar
import logging
from backports.zoneinfo import ZoneInfo

try:  # curl_cffi gives a browser-like TLS fingerprint (next.co.uk uses bot protection)
    from curl_cffi import requests
    IMPERSONATE = {"impersonate": "chrome"}
except ImportError:  # fallback
    import requests
    IMPERSONATE = {}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# basic details
PROJECT = "next"
CLIENT_NAME = ""
PROJECT_NAME = "next"
FREQUENCY = ""
BASE_URL = "https://www.next.co.uk"
COMPETITOR_NAME = "next"
CURRENCY = "GBP"


datetime_obj = datetime.now(ZoneInfo("Asia/Kolkata"))

iteration = datetime_obj.strftime("%Y_%m_%d")
YEAR = datetime_obj.strftime("%Y")
MONTH = datetime_obj.strftime("%m")
DAY = datetime_obj.strftime("%d")
MONTH_VALUE = calendar.month_abbr[int(MONTH.lstrip("0"))]
WEEK = (int(DAY) - 1) // 7 + 1
EXTRACTION_DATE = datetime_obj.strftime("%Y-%m-%d")

FILE_NAME = f"next_{iteration}"

# No MongoDB: every "collection" is a local file inside OUTPUT_DIR
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FILE_URL = os.path.join(OUTPUT_DIR, f"{FILE_NAME}_url.jsonl")            # crawler -> parser
FILE_URL_FAILED = os.path.join(OUTPUT_DIR, f"{FILE_NAME}_url_failed.jsonl")
FILE_DATA = os.path.join(OUTPUT_DIR, f"{FILE_NAME}_data.jsonl")          # parser -> export
FILE_NAME_FULLDUMP = os.path.join(OUTPUT_DIR, f"{FILE_NAME}.csv")        # final CSV
CSV_DELIMITER = ","

# proxy  (e.g. 'user:pass@host:port'); empty = no proxy
PROXY = ''
PROXIES = {"http": f"http://{PROXY}", "https": f"http://{PROXY}"} if PROXY else None

# crawl controls
START_URLS = [
    "https://www.next.co.uk/shop/womens/clothing",
    "https://www.next.co.uk/shop/mens/clothing",
]
PAGE_PARAM = "p"       # pagination -> ?p=2, ?p=3 ...
MAX_PAGES = 0          # 0 = until no new products; set e.g. 2 for a quick test
MAX_PRODUCTS = 0       # 0 = all; set e.g. 10 for a quick parser test
DELAY = 1.0            # seconds between requests
RETRIES = 3
TIMEOUT = 30


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Priority': 'u=0, i',
}


# ---- Chrome CDP (no playwright): raw websocket + HTTP ----
# Start Chrome first (Windows):
#   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-cdp"
# Then run:  python crawler.py --attach      (optional: --port=9333)
USE_CDP = "--attach" in sys.argv
CDP_PORT = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--port=")), "9222")
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
CDP_WAIT_MS = 2500   # extra wait after load so JS content appears


class CdpResponse:
    """Minimal response object (text + status_code) like requests"""

    def __init__(self, text, status_code, url):
        self.text = text
        self.status_code = status_code
        self.url = url


class CdpTab:
    """One Chrome tab driven over the DevTools websocket"""

    def __init__(self):
        import websocket  # pip install websocket-client
        # HTTP call to the open debug port: create a fresh tab
        info = requests.put(f"{CDP_URL}/json/new?about:blank", timeout=10).json()
        # suppress_origin avoids Chrome's "remote-allow-origins" 403
        self.ws = websocket.create_connection(
            info["webSocketDebuggerUrl"], timeout=TIMEOUT, suppress_origin=True
        )
        self._id = itertools.count(1)
        self.events = []
        self.send("Page.enable")
        self.send("Network.enable")
        logging.info(f"Attached to Chrome at {CDP_URL}")

    def send(self, method, params=None):
        msg_id = next(self._id)
        self.ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        while True:
            data = json.loads(self.ws.recv())
            if data.get("id") == msg_id:
                return data.get("result", {})
            if "method" in data:
                self.events.append(data)

    def get(self, url):
        self.events = []
        self.send("Page.navigate", {"url": url})

        status, deadline = 0, time.time() + TIMEOUT
        loaded = False
        while not loaded and time.time() < deadline:
            for ev in self.events:
                if ev["method"] == "Network.responseReceived" and not status \
                        and ev["params"].get("type") == "Document":
                    status = int(ev["params"]["response"]["status"])
                if ev["method"] == "Page.loadEventFired":
                    loaded = True
            self.events = []
            if not loaded:
                data = json.loads(self.ws.recv())
                if "method" in data:
                    self.events.append(data)

        time.sleep(CDP_WAIT_MS / 1000)
        # drain late events (status may arrive here)
        self.ws.settimeout(0.2)
        try:
            while True:
                data = json.loads(self.ws.recv())
                if data.get("method") == "Network.responseReceived" and not status \
                        and data["params"].get("type") == "Document":
                    status = int(data["params"]["response"]["status"])
        except Exception:
            pass
        self.ws.settimeout(TIMEOUT)

        html = self.send("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True,
        })["result"].get("value", "")
        return CdpResponse(html, status or (200 if html else 0), url)


_cdp = {}


def cdp_get(url):
    if "tab" not in _cdp:
        _cdp["tab"] = CdpTab()
    return _cdp["tab"].get(url)


def request_get(url, headers=None, params=None):
    """GET with retries. Returns response on HTTP 200, else None."""
    for attempt in range(1, RETRIES + 1):
        try:
            if USE_CDP:
                response = cdp_get(url)
            else:
                response = requests.get(
                    url, headers=headers or HEADERS, params=params,
                    proxies=PROXIES, timeout=TIMEOUT, **IMPERSONATE
                )
            if response.status_code == 200:
                return response
            logging.warning(f"{response.status_code} for {url} (attempt {attempt}/{RETRIES})")
        except Exception as error:
            logging.warning(f"{error} for {url} (attempt {attempt}/{RETRIES})")
            _cdp.pop("tab", None)  # reconnect on a broken websocket
        time.sleep(DELAY * attempt)
    return None