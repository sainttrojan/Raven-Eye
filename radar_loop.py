import os
import json
import time
import asyncio
import threading
import requests
import telebot
from scrapers.dubizzle import DubizzleScraper

TELEGRAM_TOKEN = "8718465204:AAGvGQWwzEcwjSTKLQR4Uk27DYbVPy_V-Ps"
TELEGRAM_CHAT_ID = "8291802346"
SCRAPER_API_KEY = "efda9176f26841a181772cf1f7d5602c"
DEFAULT_QUERY = "شقة للبيع مدينتي"

DB_FILE = "seen_properties.json"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
radar_is_running = True

def load_seen():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen_set):
    with open(DB_FILE, "w") as f:
        json.dump(list(seen_set), f)

async def fetch_properties(query, max_pages=1):
    scraper = DubizzleScraper([SCRAPER_API_KEY])
    results = await scraper.search(query, max_pages=max_pages)
    return results

def run_radar_iteration(query):
    print(f"Running radar iteration for: {query}")
    results = asyncio.run(fetch_properties(query, max_pages=1))
    seen = load_seen()
    new_results = []
    
    for r in results:
        if r.url not in seen:
            new_results.append(r)
            
    if not new_results:
        return 0

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
        bot.send_message(TELEGRAM_CHAT_ID, msg, parse_mode="HTML")
        seen.add(r.url)
        time.sleep(1)
        
    save_seen(seen)
    return len(new_results)

def background_radar():
    global radar_is_running
    while True:
        if radar_is_running:
            try:
                run_radar_iteration(DEFAULT_QUERY)
            except Exception as e:
                print("Radar Error:", e)
        time.sleep(10800) # 3 hours

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) != TELEGRAM_CHAT_ID:
        return
    text = (
        "أهلاً بك في نظام تحكم Raven-Eye 🦅\n\n"
        "إليك قائمة الأوامر المتاحة:\n"
        "/status - لمعرفة حالة الرادار\n"
        "/credits - لمعرفة رصيدك المتبقي في ScraperAPI\n"
        "/pause - إيقاف الرادار مؤقتاً\n"
        "/resume - إعادة تشغيل الرادار\n"
        "/search - للبحث اليدوي الآن، مثال: /search شقة مدينتي\n"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['status'])
def status(message):
    if str(message.chat.id) != TELEGRAM_CHAT_ID: return
    state = "شغال 🟢" if radar_is_running else "متوقف 🔴"
    bot.reply_to(message, f"حالة الرادار الآن: {state}")

@bot.message_handler(commands=['pause'])
def pause(message):
    if str(message.chat.id) != TELEGRAM_CHAT_ID: return
    global radar_is_running
    radar_is_running = False
    bot.reply_to(message, "تم إيقاف الرادار مؤقتاً 🔴")

@bot.message_handler(commands=['resume'])
def resume(message):
    if str(message.chat.id) != TELEGRAM_CHAT_ID: return
    global radar_is_running
    radar_is_running = True
    bot.reply_to(message, "تم إعادة تشغيل الرادار 🟢")

@bot.message_handler(commands=['credits'])
def credits(message):
    if str(message.chat.id) != TELEGRAM_CHAT_ID: return
    try:
        resp = requests.get(f"http://api.scraperapi.com/account?api_key={SCRAPER_API_KEY}")
        data = resp.json()
        used = data.get('requestCount', 0)
        limit = data.get('requestLimit', 0)
        rem = limit - used
        text = f"📊 <b>رصيد حساب ScraperAPI</b>\n\n🔹 المستخدم: {used}\n🔹 المتبقي: <b>{rem}</b>\n🔹 الحد الأقصى: {limit}"
        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء جلب الرصيد.")

@bot.message_handler(commands=['search'])
def manual_search(message):
    if str(message.chat.id) != TELEGRAM_CHAT_ID: return
    query = message.text.replace('/search', '').strip()
    if not query:
        bot.reply_to(message, "اكتب الكلمة بعد الأمر، مثال:\n/search شقة مدينتي")
        return
        
    bot.reply_to(message, f"جاري البحث عن: {query} ⏳")
    try:
        count = run_radar_iteration(query)
        if count > 0:
            bot.reply_to(message, f"تم الانتهاء! لقيت {count} نتائج جديدة وبعتها فوق ☝️")
        else:
            bot.reply_to(message, "تم الانتهاء بس مفيش شقق جديدة ظهرت.")
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء البحث.")

if __name__ == "__main__":
    print("Starting Telegram Bot and Radar...")
    threading.Thread(target=background_radar, daemon=True).start()
    bot.infinity_polling()
