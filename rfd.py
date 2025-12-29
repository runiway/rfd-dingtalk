print("【调试】程序启动（Playwright + Network）")

import os
import time
import json
import hmac
import hashlib
import base64
import urllib.parse
import requests

from playwright.sync_api import sync_playwright

# ===== 钉钉配置（GitHub Secrets）=====
DINGTALK_WEBHOOK = os.environ["DINGTALK_WEBHOOK"]
DINGTALK_SECRET = os.environ["DINGTALK_SECRET"]

URL = "https://forums.redflagdeals.com/hot-deals-f9/"
HISTORY_FILE = "sent.txt"


# ===== 钉钉签名 =====
def sign():
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{DINGTALK_SECRET}"
    hmac_code = hmac.new(
        DINGTALK_SECRET.encode(),
        string_to_sign.encode(),
        hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


def send_dingtalk(title, link):
    timestamp, sign_code = sign()
    url = f"{DINGTALK_WEBHOOK}&timestamp={timestamp}&sign={sign_code}"

    data = {
        "msgtype": "text",
        "text": {
            "content": f"🔥 RedFlagDeals\n{title}\n{link}"
        }
    }

    r = requests.post(url, json=data)
    print("【钉钉返回】", r.text)


# ===== 去重 =====
sent = set()
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        sent = set(f.read().splitlines())


# ===== Playwright Network 拦截 =====
captured_threads = []


def handle_response(response):
    try:
        url = response.url
        if "hot-deals" in url and response.request.resource_type == "xhr":
            body = response.text()
            if body and body.startswith("{"):
                data = json.loads(body)
                if isinstance(data, dict):
                    threads = data.get("threads") or data.get("data") or []
                    for t in threads:
                        title = t.get("title")
                        link = t.get("url") or t.get("link")
                        if title and link:
                            if link.startswith("/"):
                                link = "https://forums.redflagdeals.com" + link
                            captured_threads.append((title, link))
    except Exception:
        pass


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.on("response", handle_response)

    print("打开页面中…")
    page.goto(URL, wait_until="networkidle", timeout=60000)

    # 给前端足够时间发 API
    time.sleep(10)

    browser.close()


# ===== 去重 + 推送 =====
unique = []
seen_links = set()

for title, link in captured_threads:
    if link not in seen_links:
        seen_links.add(link)
        unique.append((title, link))

print("捕获到的帖子数量 =", len(unique))

for title, link in unique:
    if link in sent:
        continue

    send_dingtalk(title, link)

    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

    time.sleep(1)
