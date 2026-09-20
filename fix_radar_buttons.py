with open("radar_loop.py", "r") as f:
    code = f.read()

# We need to replace the send_welcome handler and the search handler
# It's easier to append the new markup logic and replace the specific handlers.

# First, import types from telebot
code = code.replace("import telebot", "import telebot\nfrom telebot import types")

new_handlers = """
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
"""

# I need to strip the old handlers from code.
# The old handlers start at `@bot.message_handler(commands=['start', 'help'])`
# and end right before `if __name__ == "__main__":`

start_idx = code.find("@bot.message_handler(commands=['start', 'help'])")
end_idx = code.find("if __name__ == \"__main__\":")

if start_idx != -1 and end_idx != -1:
    code = code[:start_idx] + new_handlers + code[end_idx:]
    
with open("radar_loop.py", "w") as f:
    f.write(code)
