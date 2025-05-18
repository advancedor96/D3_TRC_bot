from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import telegram
from fake_useragent import UserAgent
import asyncio
import os
from http import HTTPStatus
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# 目標網頁
URL = "https://pobyt-czasowy-zapis-na-zlozenie-wniosku.mazowieckie.pl/"
# 檢查的關鍵文字
KEY_TEXT = "Przyjmowanie zgłoszeń na złożenie wniosku o pobyt czasowy wstrzymane."
# Telegram Bot 設置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEB_UNLOCKER_API_TOKEN = os.getenv('WEB_UNLOCKER_API_TOKEN')

async def send_telegram_message(message):
    """透過 Telegram Bot 發送通知"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Bot 設置不完整")
        return False
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        return True
    except Exception as e:
        print(f"Telegram 發送失敗: {e}")
        return False

def scrape_website():
    """爬取網頁並檢查關鍵文字"""
    # 取得 +2 時區現在時間
    now = datetime.now(timezone.utc) + timedelta(hours=2)
    time_str = now.strftime("%H:%M")

    try:
        payload = {
            'url': URL,  # 替換為你的目標網站
            "zone": "my_poland_ip",
            'headers': {'User-Agent': UserAgent().random},
            'format': 'raw',
            'country': 'pl'  # 波蘭定位
        }
        headers = {
            "Authorization": f'Bearer {WEB_UNLOCKER_API_TOKEN}',
            "Content-Type": "application/json"
        }

        response = requests.post("https://api.brightdata.com/request", json=payload, headers=headers, timeout=10)

        # response = requests.get(URL, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding  # 自動偵測正確編碼

        # 解析網頁
        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text()


        # 檢查關鍵文字是否存在
        if KEY_TEXT in page_text:
            return {"status": "unchanged", "message": f"沒事 {time_str}"}
        else:
            message = f"⚠️ 網頁已更新！快去看 ({time_str})\n請檢查: {URL}"
            return {"status": "changed", "message": message}

    except requests.RequestException as e:
        message = f"爬蟲錯誤({time_str}): {str(e)}"
        return {"status": "error", "message": message}

# Vercel Serverless Function
@app.route("/api/scraper", methods=["GET", "POST"])
def scraper_api():
    result = scrape_website()
    asyncio.run(send_telegram_message(result["message"]))
    return jsonify(result)

if __name__ == "__main__":
    # 本地測試
    result = scrape_website()
    print(result["message"])
    asyncio.run(send_telegram_message(result["message"]))



