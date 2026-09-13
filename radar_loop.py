import os
import json
import time
import asyncio
import threading
import requests
import telebot
from telebot import types
from scrapers.dubizzle import DubizzleScraper

TELEGRAM_TOKEN = "8718465204:AAGvGQWwzEcwjSTKLQR4Uk27DYbVPy_V-Ps"
ADMIN_CHAT_ID = "8291802346"
SCRAPER_API_KEYS = [
    "085a9eef6828dfd6bb77a6f30ca19b3b",
    "af5da6333540757495114e2c35cf685d",
    "df094a68b9768ecf6a694cd4ab045fdb",
    "15428b0bc961dc879128ca2e8db2ab61",
    "efda9176f26841a181772cf1f7d5602c"
]
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
    scraper = DubizzleScraper(SCRAPER_API_KEYS)
    results = await scraper.search(query, max_pages=max_pages)
    return results

def is_valid_result(r, query):
    text = (r.title + " " + r.description).lower()
    
    if "مدينتي" in query and "مدينتي" not in text:
        return False
        
    if "مدينتي" in query:
        bad_cities = ["الشروق", "بدر", "الرحاب", "المستقبل", "التجمع", "العاصمة", "العبور", "هيليوبوليس"]
        for bc in bad_cities:
            if bc in text:
                return False
                
    bad_keywords = ["شركة", "بروكر", "عمولة", "تسويق", "وسيط", "مكتب", "سمسار", "عقارات"]
    for bk in bad_keywords:
        if bk in text:
            return False
            
    return True

def run_radar_iteration(query, target_chat_id=None):
    print(f"Running radar iteration for: {query}")
    results = asyncio.run(fetch_properties(query, max_pages=1))
    seen = load_seen()
    new_results = []
    
    for r in results:
        if r.url not in seen and is_valid_result(r, query):
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
    total_rem = 0
    for key in SCRAPER_API_KEYS:
        try:
            resp = requests.get(f"http://api.scraperapi.com/account?api_key={key}", timeout=5)
            data = resp.json()
            used = data.get('requestCount', 0)
            limit = data.get('requestLimit', 0)
            total_rem += max(0, limit - used)
        except:
            pass
    return total_rem

def background_radar():
    global radar_is_running
    warning_sent = False
    while True:
        if radar_is_running:
            rem = check_credits_internal()
            
            if rem <= 50 and not warning_sent:
                try:
                    bot.send_message(ADMIN_CHAT_ID, f"⚠️ <b>تحذير هام:</b>\nرصيدك في ScraperAPI يوشك على النفاذ! المتبقي: <b>{rem}</b> نقطة فقط.", parse_mode="HTML")
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

def get_main_keyboard(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    item_search = types.KeyboardButton('🔍 بحث جديد')
    
    if str(chat_id) == ADMIN_CHAT_ID:
        item_status = types.KeyboardButton('📊 حالة الرادار')
        item_credits = types.KeyboardButton('💰 الرصيد')
        item_pause = types.KeyboardButton('⏸️ إيقاف الرادار')
        item_resume = types.KeyboardButton('▶️ تشغيل الرادار')
        item_restart = types.KeyboardButton('🔄 ريستارت')
        markup.add(item_search, item_status, item_credits, item_pause, item_resume, item_restart)
    else:
        markup.add(item_search)
        
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = str(message.chat.id)
    subs = load_subscribers()
    if chat_id not in subs:
        subs.add(chat_id)
        save_subscribers(subs)
        
    text = "أهلاً بك في نظام تحكم Raven-Eye 🦅\nاستخدم الأزرار بالأسفل للتحكم:"
    bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard(chat_id))

@bot.message_handler(func=lambda message: message.text in ['📊 حالة الرادار', '/status'])
def status_btn(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    state = "شغال 🟢" if radar_is_running else "متوقف 🔴"
    bot.reply_to(message, f"حالة الرادار الآن: {state}")

@bot.message_handler(func=lambda message: message.text in ['⏸️ إيقاف الرادار', '/pause'])
def pause_btn(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    global radar_is_running
    radar_is_running = False
    bot.reply_to(message, "تم إيقاف الرادار مؤقتاً 🔴")

@bot.message_handler(func=lambda message: message.text in ['▶️ تشغيل الرادار', '/resume'])
def resume_btn(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    global radar_is_running
    radar_is_running = True
    bot.reply_to(message, "تم إعادة تشغيل الرادار 🟢")

@bot.message_handler(func=lambda message: message.text in ['🔄 ريستارت', '/restart'])
def restart_btn(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    bot.reply_to(message, "جاري إعادة تشغيل نظام الرادار... 🔄")
    import sys, os
    os.execv(sys.executable, ['python'] + sys.argv)

@bot.message_handler(func=lambda message: message.text in ['💰 الرصيد', '/credits'])
def credits_btn(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    bot.reply_to(message, "جاري فحص جميع الحسابات... ⏳")
    try:
        total_used = 0
        total_limit = 0
        total_rem = 0
        for key in SCRAPER_API_KEYS:
            try:
                resp = requests.get(f"http://api.scraperapi.com/account?api_key={key}", timeout=5)
                data = resp.json()
                used = data.get('requestCount', 0)
                limit = data.get('requestLimit', 0)
                total_used += used
                total_limit += limit
                total_rem += max(0, limit - used)
            except: pass

        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء جلب الرصيد.")

@bot.message_handler(func=lambda message: message.text in ['🔍 بحث جديد', '/search'])
def manual_search_btn(message):
    msg = bot.reply_to(message, "اكتب الكلمة اللي عايز تبحث عنها دلوقتي (مثال: شقة للبيع مدينتي):")
    bot.register_next_step_handler(msg, process_search_query)

def process_search_query(message):
    query = message.text.strip()
    if not query: return
    bot.reply_to(message, f"جاري البحث عن: {query} ⏳")
    try:
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
