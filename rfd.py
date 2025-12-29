print("【调试】程序已经开始运行")

import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
import os
import re

# ===== 钉钉机器人配置（从 GitHub Secrets 读取）=====
DINGTALK_WEBHOOK = os.environ["DINGTALK_WEBHOOK"]
DINGTALK_SECRET = os.environ["DINGTALK_SECRET"]

# ===== RedFlagDeals 热帖页面（HTML）=====
URL = "https://forums.redflagdeals.com/hot-deals-f9/"

# ===== 去重文件 =====
HISTORY_FILE = "sent.txt"


def sign():
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{DINGTALK_SECRET}"
    hmac_code = hmac.new(
        DINGTALK_SECRET.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


def send_dingtalk(title, link):
    timestamp, sign_code = sign()
    url = f"{DINGTALK_WEBHOOK}&timestamp={timestamp}&sign={sign_code}"

    text = f"""🔥 RedFlagDeals 新 Deal
----------------------
{title}
{link}
"""

    data = {
        "msgtype": "text",
        "text": {"content": text}
    }

    resp = requests.post(url, json=data)
    print("【钉钉返回】", resp.text)


def load_sent():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(f.read().splitlines())


def save_sent(link):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")


# ===== 主程序 =====
sent = load_sent()

headers = {
    "User-Agent": "Mozilla/5.0"
}

resp = requests.get(URL, headers=headers, timeout=20)
html = resp.text

matches = re.findall(
    r'<a[^>]+class="topic_title_link[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    html,
    re.S
)

print("抓到的 Deal 数量 =", len(matches))

for link, title in matches:
    title = re.sub("<.*?>", "", title).strip()
    full_link = "https://forums.redflagdeals.com" + link

    if full_link in sent:
        continue

    send_dingtalk(title, full_link)
    save_sent(full_link)
    time.sleep(1)
