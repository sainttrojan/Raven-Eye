import os
import json
import time
import asyncio
import requests
from scrapers.dubizzle import DubizzleScraper

TELEGRAM_TOKEN = "8718465204:AAGvGQWwzEcwjSTKLQR4Uk27DYbVPy_V-Ps"
TELEGRAM_CHAT_ID = "8291802346"
SCRAPER_API_KEY = "efda9176f26841a181772cf1f7d5602c"
QUERY = "شقة للبيع مدينتي"

DB_FILE = "seen_properties.json"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Error sending message:", e)

def load_seen():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen_set):
    with open(DB_FILE, "w") as f:
        json.dump(list(seen_set), f)

async def run_radar():
    print("Running radar for query:", QUERY)
    scraper = DubizzleScraper([SCRAPER_API_KEY])
    
    # Fetch only 1 page to save credits during automated checks
    results = await scraper.search(QUERY, max_pages=1)
    
    seen = load_seen()
    new_results = []
    
    for r in results:
        # We use URL as unique identifier
        if r.url not in seen:
            new_results.append(r)
    
    if not new_results:
        print("No new properties found this time.")
        return

    # Prevent spam on first run: if database was empty, only send top 3
    if len(seen) == 0:
        new_results = new_results[:3]
        
    for r in new_results:
        price_text = r.price if r.price else "غير محدد"
        area_text = r.area if r.area else "غير محدد"
        msg = (
            f"🚨 <b>عقار جديد متاح!</b>\n\n"
            f"📌 <b>العنوان:</b> {r.title}\n"
            f"💰 <b>السعر:</b> {price_text}\n"
            f"📏 <b>المساحة:</b> {area_text}\n"
            f"📝 <b>التفاصيل:</b> {r.description}\n\n"
            f"🔗 <a href='{r.url}'>رابط الإعلان</a>"
        )
        send_telegram_message(msg)
        seen.add(r.url)
        time.sleep(1) # sleep briefly to avoid telegram rate limits
        
    save_seen(seen)
    print(f"Sent {len(new_results)} new properties to Telegram.")

def start_loop():
    print("Radar loop started...")
    while True:
        try:
            asyncio.run(run_radar())
        except Exception as e:
            print("Radar loop error:", e)
        # Wait 3 hours between checks to conserve ScraperAPI credits
        # 3 hours = 10800 seconds
        time.sleep(10800)

if __name__ == "__main__":
    start_loop()
