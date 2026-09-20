user_search_state = {}
user_osint_state = {}
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
    """Check remaining ZenRows credits (primary scraping engine)."""
    try:
        from core.config import load_zenrows_key
        key = load_zenrows_key()
        resp = requests.get(
            f"https://api.zenrows.com/v1/credits",
            params={"apikey": key},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("remaining", 9999)
    except Exception as e:
        print(f"ZenRows credits check failed: {e}")
    return 9999  # assume credits available if we can't check


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
        item_broker = types.KeyboardButton('🕵️ فحص سمسار (OSINT)')
        item_phone = types.KeyboardButton('📱 فحص رقم (OSINT)')
        markup.row(item_search, item_status)
        markup.row(item_broker, item_phone)
        markup.row(item_credits, item_pause, item_resume)
        markup.row(item_restart)
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
    bot.reply_to(message, "جاري فحص رصيد ZenRows... ⏳")
    try:
        from core.config import load_zenrows_key
        key = load_zenrows_key()
        resp = requests.get(
            "https://api.zenrows.com/v1/credits",
            params={"apikey": key},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            remaining = data.get("remaining", "غير معروف")
            used      = data.get("used", "غير معروف")
            total     = data.get("total", "غير معروف")
            lines = [
                "📊 <b>رصيد ZenRows (محرك السحب الأساسي)</b>",
                "",
                f"✅ المتبقي: <b>{remaining}</b> طلب",
                f"🔹 المستخدم: {used}",
                f"🔹 الإجمالي: {total}",
            ]
        else:
            lines = [f"⚠️ تعذر جلب الرصيد — كود: {resp.status_code}", resp.text[:100]]
        bot.reply_to(message, "\n".join(lines), parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء جلب الرصيد: {e}")



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
        is_deep = len(parts) > 3 and parts[3].lower() == "deep"
        modules_arg = None if is_deep else "github,instagram,facebook,tiktok,twitter,snapchat,telegram"
        
        from core.broker_osint import scan_username, scan_email
        if kind == "email":
            res = scan_email(value, modules=modules_arg, timeout=900 if is_deep else 300, cross_scan=is_deep, allow_loud=is_deep)
        else:
            res = scan_username(value, modules=modules_arg, timeout=900 if is_deep else 300, cross_scan=is_deep, allow_loud=is_deep)
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
        
        try:
            from core.report_generator import generate_osint_excel, generate_osint_pdf
            import os
            
            bot.send_message(message.chat.id, "جاري تحضير ملفات الـ Excel والـ PDF... ⏳")
            excel_file = f"investigate_{value}.xlsx"
            pdf_file = f"investigate_{value}.pdf"
            
            generate_osint_excel(res, kind, value, excel_file)
            generate_osint_pdf(res, kind, value, pdf_file)
            
            with open(excel_file, "rb") as f_xls:
                bot.send_document(message.chat.id, f_xls)
            with open(pdf_file, "rb") as f_pdf:
                bot.send_document(message.chat.id, f_pdf)
                
            os.remove(excel_file)
            os.remove(pdf_file)
        except Exception as file_e:
            print("Failed to send files:", file_e)
            
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
            
        with_web = len(parts) > 2 and parts[2].lower() == "with_web"
        if with_web:
            lines.append("جاري البحث في جوجل... 🔍")
            try:
                from core.phone_osint import web_footprint
                from core.config import load_api_keys
                wres = web_footprint(parts[1].strip(), load_api_keys(), max_pages=2)
                res["web_footprint"] = wres
                if wres.get("ok") and wres.get("count") > 0:
                    lines.append(f"تم العثور على {wres['count']} نتيجة في جوجل!")
                elif wres.get("ok"):
                    lines.append("لا يوجد ظهور للرقم في جوجل.")
                else:
                    lines.append("تعذر البحث في جوجل.")
            except Exception as we:
                print("Web footprint error:", we)

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
        
        try:
            from core.report_generator import generate_osint_excel, generate_osint_pdf
            import os
            
            if 'db_correlation' not in res:
                res['db_correlation'] = corr if 'corr' in locals() else {}
                
            bot.send_message(message.chat.id, "جاري تحضير ملفات الـ Excel والـ PDF... ⏳")
            excel_file = f"phone_{parts[1].strip()}.xlsx"
            pdf_file = f"phone_{parts[1].strip()}.pdf"
            
            generate_osint_excel(res, "phone", parts[1].strip(), excel_file)
            generate_osint_pdf(res, "phone", parts[1].strip(), pdf_file)
            
            with open(excel_file, "rb") as f_xls:
                bot.send_document(message.chat.id, f_xls)
            with open(pdf_file, "rb") as f_pdf:
                bot.send_document(message.chat.id, f_pdf)
                
            os.remove(excel_file)
            os.remove(pdf_file)
        except Exception as file_e:
            print("Failed to send files:", file_e)
            
    except Exception as e:
        print(f"CheckPhone Error: {e}")
        bot.reply_to(message, "حدث خطأ أثناء فحص الرقم.")



@bot.message_handler(func=lambda message: message.text in ['🕵️ فحص سمسار (OSINT)'])
def investigate_ui_btn(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    msg = bot.reply_to(message, "ابعت اليوزرنيم أو الإيميل بتاع السمسار اللي عايز تفحصه:\n(مثال: broker_name أو mail@example.com)")
    bot.register_next_step_handler(msg, step_investigate_target)

def step_investigate_target(message):
    if not message.text: return
    chat_id = str(message.chat.id)
    val = message.text.strip()
    kind = "email" if "@" in val else "username"
    user_osint_state[chat_id] = {"type": "investigate", "kind": kind, "target": val}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("سريع (أشهر المواقع فقط - 30 ثانية)", callback_data="osint_inv_fast"),
        types.InlineKeyboardButton("عميق (كل المواقع - قد يستغرق دقائق)", callback_data="osint_inv_deep")
    )
    bot.send_message(message.chat.id, "اختار نوع الفحص:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('osint_inv_'))
def step_investigate_type(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_osint_state: return
    is_deep = call.data == "osint_inv_deep"
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="جاري بدء الفحص... ⏳")
    
    msg = call.message
    msg.text = f"/investigate {user_osint_state[chat_id]['kind']} {user_osint_state[chat_id]['target']} {'deep' if is_deep else 'fast'}"
    threading.Thread(target=investigate_cmd, args=(msg,)).start()


@bot.message_handler(func=lambda message: message.text in ['📱 فحص رقم (OSINT)'])
def checkphone_ui_btn(message):
    if str(message.chat.id) != ADMIN_CHAT_ID: return
    msg = bot.reply_to(message, "ابعت رقم الموبايل اللي عايز تفحصه:\n(مثال: 01001234567)")
    bot.register_next_step_handler(msg, step_checkphone_target)

def step_checkphone_target(message):
    if not message.text: return
    chat_id = str(message.chat.id)
    val = message.text.strip()
    user_osint_state[chat_id] = {"type": "checkphone", "target": val}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("عادي (بيانات وحسابات فقط)", callback_data="osint_ph_normal"),
        types.InlineKeyboardButton("شامل + جوجل (البحث عن الرقم فالويب)", callback_data="osint_ph_web")
    )
    bot.send_message(message.chat.id, "اختار نوع الفحص:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('osint_ph_'))
def step_checkphone_type(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_osint_state: return
    with_web = call.data == "osint_ph_web"
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="جاري بدء الفحص... ⏳")
    
    msg = call.message
    msg.text = f"/checkphone {user_osint_state[chat_id]['target']} {'with_web' if with_web else 'normal'}"
    threading.Thread(target=checkphone_cmd, args=(msg,)).start()


if __name__ == "__main__":
    print("Starting Telegram Bot and Radar...")
    threading.Thread(target=background_radar, daemon=True).start()
    bot.infinity_polling()
