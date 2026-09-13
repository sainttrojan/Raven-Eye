import os
import json
import time
import asyncio
import threading
import requests
import telebot
from scrapers.dubizzle import DubizzleScraper

TELEGRAM_TOKEN = "8718465204:AAGvGQWwzEcwjSTKLQR4Uk27DYbVPy_V-Ps"
ADMIN_CHAT_ID = "8291802346"
SCRAPER_API_KEY = "efda9176f26841a181772cf1f7d5602c"
DEFAULT_QUERIES = ["شقة للبيع في مدينتي من المالك", "شقة للايجار في مدينتي من المالك"]

DB_FILE = "seen_properties.json"
SUBS_FILE = "subscribers.json"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
radar_is_running = True

def load_subscribers():
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            return set(json.load(f))
    return {ADMIN_CHAT_ID}

def save_subscribers(subs_set):
    with open(SUBS_FILE, "w") as f:
        json.dump(list(subs_set), f)

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

def run_radar_iteration(query, target_chat_id=None):
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
        
    subs = load_subscribers()
    if target_chat_id:
        subs = {target_chat_id}
        
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
        
        for chat_id in subs:
            try:
                bot.send_message(chat_id, msg, parse_mode="HTML")
            except Exception as e:
                print(f"Failed to send to {chat_id}: {e}")
                
        seen.add(r.url)
        time.sleep(1)
        
    save_seen(seen)
    return len(new_results)

def check_credits_internal():
    try:
        resp = requests.get(f"http://api.scraperapi.com/account?api_key={SCRAPER_API_KEY}")
        data = resp.json()
        used = data.get('requestCount', 0)
        limit = data.get('requestLimit', 0)
        return limit - used
    except:
        return 9999

def background_radar():
    global radar_is_running
    warning_sent = False
    while True:
        if radar_is_running:
            rem = check_credits_internal()
            
            if rem <= 50 and not warning_sent:
                try:
                    bot.send_message(ADMIN_CHAT_ID, f"⚠️ <b>تحذير هام:</b>
رصيدك في ScraperAPI يوشك على النفاذ! المتبقي: <b>{rem}</b> نقطة فقط.", parse_mode="HTML")
                except: pass
                warning_sent = True
            elif rem > 50:
                warning_sent = False
                
            if rem > 0:
                for q in DEFAULT_QUERIES:
                    try:
                        run_radar_iteration(q)
                    except Exception as e:
                        print("Radar Error:", e)
                    time.sleep(10) # 10 seconds between different queries
            else:
                print("Skipping radar run because credits are empty.")
        time.sleep(10800) # 3 hours

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = str(message.chat.id)
    subs = load_subscribers()
    if chat_id not in subs:
        subs.add(chat_id)
        save_subscribers(subs)
        bot.reply_to(message, "مرحباً بك! تم تفعيل إشعارات رادار Raven-Eye 🦅\nسيصلك كل جديد فور نزوله.")
    
    text = (
        "أهلاً بك في نظام تحكم Raven-Eye 🦅\n\n"
        "اليك قائمة الأوامر المتاحة لك:\n"
        "/search - للبحث اليدوي الآن، مثال: /search شقة مدينتي\n"
    )
    
    if chat_id == ADMIN_CHAT_ID:
        text += (
            "\n👑 أوامر الإدارة الخاصة بك فقط:\n"
            "/status - لمعرفة حالة الرادار\n"
            "/credits - لمعرفة رصيدك المتبقي في ScraperAPI\n"
            "/pause - إيقاف الرادار مؤقتاً لجميع المستخدمين\n"
            "/resume - إعادة تشغيل الرادار\n            /restart - عمل ريستارت كامل للبوت\n"
        )
        
    bot.reply_to(message, text)

@bot.message_handler(commands=['restart'])
def restart_bot(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    bot.reply_to(message, "جاري إعادة تشغيل نظام الرادار... 🔄")
    import sys
    import os
    os.execv(sys.executable, ['python'] + sys.argv)

@bot.message_handler(commands=['status'])
def status(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    state = "شغال 🟢" if radar_is_running else "متوقف 🔴"
    bot.reply_to(message, f"حالة الرادار الآن: {state}")

@bot.message_handler(commands=['pause'])
def pause(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    global radar_is_running
    radar_is_running = False
    bot.reply_to(message, "تم إيقاف الرادار مؤقتاً 🔴")

@bot.message_handler(commands=['resume'])
def resume(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    global radar_is_running
    radar_is_running = True
    bot.reply_to(message, "تم إعادة تشغيل الرادار 🟢")

@bot.message_handler(commands=['credits'])
def credits(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
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
    query = message.text.replace('/search', '').strip()
    if not query:
        bot.reply_to(message, "اكتب الكلمة بعد الأمر، مثال:\n/search شقة مدينتي")
        return
        
    bot.reply_to(message, f"جاري البحث عن: {query} ⏳")
    try:
        # Pass target_chat_id so search results only go to the person who asked!
        count = run_radar_iteration(query, target_chat_id=str(message.chat.id))
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
