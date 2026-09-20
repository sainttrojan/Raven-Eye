import re

with open("radar_loop.py", "r") as f:
    code = f.read()

# Replace the single SCRAPER_API_KEY with a list of keys
old_key = 'SCRAPER_API_KEY = "efda9176f26841a181772cf1f7d5602c"'
new_keys = """SCRAPER_API_KEYS = [
    "085a9eef6828dfd6bb77a6f30ca19b3b",
    "af5da6333540757495114e2c35cf685d",
    "df094a68b9768ecf6a694cd4ab045fdb",
    "15428b0bc961dc879128ca2e8db2ab61",
    "efda9176f26841a181772cf1f7d5602c"
]"""
code = code.replace(old_key, new_keys)

# Replace the scraper instantiation
code = code.replace("DubizzleScraper([SCRAPER_API_KEY])", "DubizzleScraper(SCRAPER_API_KEYS)")

# Rewrite check_credits_internal to check ALL keys
old_check = """def check_credits_internal():
    try:
        resp = requests.get(f"http://api.scraperapi.com/account?api_key={SCRAPER_API_KEY}")
        data = resp.json()
        used = data.get('requestCount', 0)
        limit = data.get('requestLimit', 0)
        return limit - used
    except:
        return 9999"""

new_check = """def check_credits_internal():
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
    return total_rem"""
code = code.replace(old_check, new_check)

# Rewrite the telegram credits command
old_credits_cmd = """@bot.message_handler(func=lambda message: message.text in ['💰 الرصيد', '/credits'])
def credits_btn(message):
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
        bot.reply_to(message, "حدث خطأ أثناء جلب الرصيد.")"""

new_credits_cmd = """@bot.message_handler(func=lambda message: message.text in ['💰 الرصيد', '/credits'])
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
        text = f"📊 <b>إجمالي رصيد جميع الحسابات</b>\n\n🔹 المستخدم الكلي: {total_used}\n🔹 المتبقي الكلي: <b>{total_rem}</b>\n🔹 الحد الأقصى الكلي: {total_limit}"
        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء جلب الرصيد.")"""
code = code.replace(old_credits_cmd, new_credits_cmd)

# Same for app.py just in case the web UI uses it? We'll ignore app.py for now as they are asking about Telegram

with open("radar_loop.py", "w") as f:
    f.write(code)
