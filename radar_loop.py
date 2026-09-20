user_search_state = {}
import os
import json
import time
import asyncio
import threading
import requests
import telebot
from telebot import types
from dotenv import load_dotenv
load_dotenv()
from scrapers.dubizzle import DubizzleScraper
from scrapers.google import GoogleScraper
from core.config import load_api_keys


TELEGRAM_TOKEN = "8718465204:AAGvGQWwzEcwjSTKLQR4Uk27DYbVPy_V-Ps"
ADMIN_CHAT_ID = "8291802346"

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
    scraper = DubizzleScraper(load_api_keys())
    results = await scraper.search(query, max_pages=max_pages)
    return results

def escape_html(text):
    if not text: return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def is_valid_result(r, query):
    if r.price:
        import re
        digits = re.sub(r'[^0-9]', '', str(r.price))
        if digits:
            try:
                if int(digits) <= 12000:
                    return False
            except:
                pass
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
            f"📌 <b>العنوان:</b> {escape_html(r.title)}\n"
            f"💰 <b>السعر:</b> {price_text}\n"
            f"📏 <b>المساحة:</b> {area_text}\n"
            f"📝 <b>التفاصيل:</b> {escape_html(r.description)}\n\n"
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
    for key in load_api_keys():
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
        for key in load_api_keys():
            try:
                resp = requests.get(f"http://api.scraperapi.com/account?api_key={key}", timeout=5)
                data = resp.json()
                used = data.get('requestCount', 0)
                limit = data.get('requestLimit', 0)
                total_used += used
                total_limit += limit
                total_rem += max(0, limit - used)
            except: pass
            
        lines = [
            "📊 <b>إجمالي رصيد جميع الحسابات</b>",
            "",
            f"🔹 المستخدم الكلي: {total_used}",
            f"🔹 المتبقي الكلي: <b>{total_rem}</b>",
            f"🔹 الحد الأقصى الكلي: {total_limit}"
        ]
        text = "\n".join(lines)
        
        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء جلب الرصيد.")


@bot.message_handler(func=lambda message: message.text in ['🔍 بحث جديد', '/search'])
def manual_search_btn(message):
    chat_id = str(message.chat.id)
    user_search_state[chat_id] = {}
    msg = bot.reply_to(message, "اكتب الكلمة اللي عايز تبحث عنها (مثال: شقة للبيع مدينتي):")
    bot.register_next_step_handler(msg, step_keyword)

def step_keyword(message):
    chat_id = str(message.chat.id)
    if not message.text: return
    user_search_state[chat_id]['query'] = message.text.strip()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("جميع المواقع", callback_data="site_all"),
        types.InlineKeyboardButton("Dubizzle فقط", callback_data="site_dubizzle"),
        types.InlineKeyboardButton("PropertyFinder فقط", callback_data="site_pf"),
        types.InlineKeyboardButton("Aqarmap فقط", callback_data="site_aqarmap")
    )
    bot.send_message(message.chat.id, "اختار الموقع اللي عايز تبحث فيه:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('site_'))
def step_site(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_search_state: return
    
    site_map = {
        "site_all": "جميع المواقع",
        "site_dubizzle": "Dubizzle فقط",
        "site_pf": "PropertyFinder فقط",
        "site_aqarmap": "Aqarmap فقط"
    }
    user_search_state[chat_id]['site'] = site_map.get(call.data, "جميع المواقع")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("أي وقت", callback_data="time_any"),
        types.InlineKeyboardButton("آخر 24 ساعة", callback_data="time_24h"),
        types.InlineKeyboardButton("آخر أسبوع", callback_data="time_week")
    )
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=f"تم اختيار: {user_search_state[chat_id]['site']}\n\nاختار تاريخ النشر:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
def step_time(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_search_state: return
    
    time_map = {
        "time_any": "أي وقت",
        "time_24h": "آخر 24 ساعة",
        "time_week": "آخر أسبوع"
    }
    user_search_state[chat_id]['time'] = time_map.get(call.data, "أي وقت")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("نعم، تطابق حرفي", callback_data="exact_yes"),
        types.InlineKeyboardButton("لا، بحث عادي", callback_data="exact_no")
    )
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=f"تم اختيار: {user_search_state[chat_id]['time']}\n\nهل تريد تطابق الجملة بالكامل؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('exact_'))
def step_exact(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_search_state: return
    
    exact = True if call.data == "exact_yes" else False
    user_search_state[chat_id]['exact'] = exact
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("1 صفحة (أسرع وأوفر)", callback_data="pages_1"),
        types.InlineKeyboardButton("3 صفحات", callback_data="pages_3"),
        types.InlineKeyboardButton("5 صفحات (دقيق)", callback_data="pages_5")
    )
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text="اختر عدد الصفحات التي تريد البحث فيها (كلما زاد العدد، زاد استهلاك الرصيد):", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pages_'))
def step_pages(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_search_state: return
    
    pages = int(call.data.split('_')[1])
    user_search_state[chat_id]['pages'] = pages
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="جاري البحث بناءً على اختياراتك... ⏳")
    
    # Run the search asynchronously
    threading.Thread(target=execute_custom_search, args=(chat_id, user_search_state[chat_id])).start()

def execute_custom_search(chat_id, state):
    max_pages = state.get('pages', 3)
    query = state['query']
    site_option = state['site']
    time_option = state['time']
    exact_match = state['exact']
    
    final_query = query
    if exact_match:
        final_query = f'"{query}"'
        
    if site_option == "PropertyFinder فقط":
        final_query += " site:propertyfinder.eg"
    elif site_option == "Dubizzle فقط":
        # Dubizzle is handled separately, but for Google fallback we need the site parameter
        pass 
    elif site_option == "Aqarmap فقط":
        final_query += " site:aqarmap.com.eg"
        
    time_filter = ""
    if time_option == "آخر 24 ساعة":
        time_filter = "qdr:d"
    elif time_option == "آخر أسبوع":
        time_filter = "qdr:w"
        
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def fetch():
            if site_option == "Dubizzle فقط":
                scraper = DubizzleScraper(load_api_keys())
                return await scraper.search(query, time_filter, max_pages=max_pages)
            else:
                scraper = GoogleScraper(load_api_keys())
                return await scraper.search(final_query, time_filter, max_pages=max_pages)
                
        results = loop.run_until_complete(fetch())
        
        if results:
            bot.send_message(chat_id, f"✅ تم العثور على {len(results)} نتائج. جاري إرسالها...")
            for r in results[:15]: # Limit to 15 to avoid telegram spam
                price_text = r.price if r.price else "غير محدد"
                area_text = r.area if r.area else "غير محدد"
                msg = (
                    f"📌 <b>العنوان:</b> {escape_html(r.title)}\n"
                    f"💰 <b>السعر:</b> {price_text}\n"
                    f"📏 <b>المساحة:</b> {area_text}\n"
                    f"📝 <b>التفاصيل:</b> {escape_html(r.description)}\n\n"
                    f"🔗 <a href='{r.url}'>رابط الإعلان</a>"
                )
                bot.send_message(chat_id, msg, parse_mode="HTML")
                time.sleep(1)
            if len(results) > 15:
                bot.send_message(chat_id, f"تم إخفاء {len(results) - 15} نتيجة إضافية لتجنب الإزعاج.")
        else:
            bot.send_message(chat_id, "❌ لم يتم العثور على أي نتائج مطابقة لاختياراتك.")
            
    except Exception as e:
        bot.send_message(chat_id, "⚠️ حدث خطأ أثناء البحث.")
        print(f"Custom Search Error: {e}")


@bot.message_handler(commands=['investigate'])
def investigate_cmd(message):
    """Usage: /investigate username johndoe  OR  /investigate email a@b.com"""
    if str(message.chat.id) != ADMIN_CHAT_ID:
        return
    try:
        parts = (message.text or "").split()
        if len(parts) < 3:
            bot.reply_to(message, "الاستخدام:\n/investigate username broker_eg\n/investigate email mail@example.com")
            return
        kind, value = parts[1].lower(), parts[2].strip()
        if kind not in ("username", "email"):
            bot.reply_to(message, "النوع لازم يكون username أو email")
            return
        bot.reply_to(message, f"جاري فحص {value} عبر user-scanner... ⏳ (قد يستغرق دقيقة)")
        from core.broker_osint import scan_username, scan_email
        if kind == "email":
            res = scan_email(value, modules="github,instagram,facebook", timeout=300)
        else:
            res = scan_username(value, modules="github,instagram,facebook", timeout=300)
        if not res.get("ok"):
            bot.reply_to(message, f"فشل الفحص: {res.get('error')}")
            return
        hits = res.get("hits", [])
        lines = [f"نتيجة فحص {value}: {res['total_hits']} مؤكدة من {res['total_checked']}"]
        for h in hits[:10]:
            lines.append(f"- {h.get('site_name')}: {h.get('url')}")
        if len(hits) > 10:
            lines.append(f"... و {len(hits) - 10} نتائج أخرى")
        try:
            from core.db import DatabaseManager
            DatabaseManager().save_osint_result(kind, value, res["total_hits"],
                                                res["total_checked"], hits, "")
        except Exception:
            pass
        bot.reply_to(message, "\n".join(lines) or "لا توجد نتائج مؤكدة.")
    except Exception as e:
        print(f"Investigate Error: {e}")
        bot.reply_to(message, "حدث خطأ أثناء الفحص.")


@bot.message_handler(commands=['checkphone'])
def checkphone_cmd(message):
    """Usage: /checkphone 01001234567"""
    if str(message.chat.id) != ADMIN_CHAT_ID:
        return
    try:
        parts = (message.text or "").split()
        if len(parts) < 2:
            bot.reply_to(message, "الاستخدام:\n/checkphone 01001234567")
            return
        bot.reply_to(message, f"جاري فحص {parts[1]}... ⏳")
        from core.phone_osint import full_check, find_in_database
        res = full_check(parts[1].strip(), with_accounts=True, timeout=15)
        if not res.get("ok"):
            bot.reply_to(message, f"رقم غير صالح: {res.get('error')}")
            return
        lines = [f"الرقم: {res['e164']}",
                 f"الشركة: {res.get('carrier')} | صالح: {'نعم' if res.get('valid') else 'لا'}"]
        for a in res.get("accounts", []):
            mark = "مسجل" if a.get("exists") else ("rate limit" if a.get("rate_limited") else "غير مسجل")
            lines.append(f"- {a.get('domain')}: {mark}")
        try:
            corr = find_in_database(parts[1].strip())
            if corr.get("ok"):
                if corr["count"]:
                    lines.append(f"ظهر في {corr['count']} إعلان محفوظ عندنا")
                else:
                    lines.append("مش موجود في إعلاناتنا المحفوظة (معلن جديد غالبا)")
        except Exception:
            pass
        links = res.get("links", {})
        if links.get("whatsapp"):
            lines.append(f"واتساب: {links['whatsapp']}")
        try:
            from core.db import DatabaseManager
            DatabaseManager().save_phone_osint(res["e164"], res.get("carrier", ""),
                                               bool(res.get("valid")), res.get("accounts", []), "")
        except Exception:
            pass
        bot.reply_to(message, "\n".join(lines))
    except Exception as e:
        print(f"CheckPhone Error: {e}")
        bot.reply_to(message, "حدث خطأ أثناء فحص الرقم.")


if __name__ == "__main__":
    print("Starting Telegram Bot and Radar...")
    threading.Thread(target=background_radar, daemon=True).start()
    bot.infinity_polling()
